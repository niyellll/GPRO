#!/usr/bin/env python3
"""CSB Klarin state + claim attachments transfer, never triggered by CI.

Default DRY RUN: reads only two pinned Supabase projects.
--apply is operator-only: requires full isolated restore proof, externally
frozen writes, snapshot versions/hashes, and locally SHA256-proved copies of
EVERY private source/target attachment byte. No bucket file transfer here.

Actual private objects MUST already be staged to target using authenticated
Storage tooling and the correct tenant bucket, before metadata/state transfer.
Cross-project Storage+Postgres is NOT an atomic transaction: rollback and
retention are an independent release gate.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, unquote, urlsplit

SOURCE_REF="krwoiucqfcijmihnrlem"
TARGET_REF="numlkqppirrxfwdhazja"
SOURCE_SCHEMA="public"
TARGET_SCHEMA="csb_klarin"
SOURCE_BUCKET="klarin-private-attachments"
TARGET_BUCKET="gpro-csb-private-attachments"
TABLES=("klarin_stock_claim_app_state","klarin_stock_claim_attachments","klarin_realtime_signal")
ATTACH_COLUMNS=(
    "id","owner_type","owner_id","file_name","mime_type","size_bytes",
    "data_base64","uploaded_by","created_at","storage_path","storage_migrated_at",
)
STATE_KEY="default"


class TransferBlocked(ValueError):
    pass


def require_operator_url(raw: str, project_ref: str) -> None:
    """Only server-owner postgres roles on pinned project and strict TLS."""
    try:
        u=urlsplit(raw)
        host=(u.hostname or "").lower()
        user=unquote(u.username or "")
        direct=(host=="db."+project_ref+".supabase.co" and user=="postgres" and
                (u.port is None or u.port==5432))
        pooler=(bool(re.fullmatch(r"[a-z0-9-]+\\.pooler\\.supabase\\.com",host)) and
                user=="postgres."+project_ref and u.port in (5432,6543))
        opts=parse_qs(u.query,keep_blank_values=True,strict_parsing=True) if u.query else {}
        ssl=opts.get("sslmode",["require"])
        if not (
            u.scheme in ("postgresql","postgres") and (direct or pooler) and
            bool(u.password) and u.path=="/postgres" and not u.fragment and
            set(opts).issubset({"sslmode"}) and len(ssl)==1 and
            ssl[0] in ("require","verify-full")
        ):
            raise TransferBlocked("Wrong project, privileged login, protocol or TLS")
    except (ValueError,TypeError):
        raise TransferBlocked("Supabase operator connection not allowlisted") from None


def state_digest(state: object) -> str:
    # For an existing state parsed from PostgreSQL JSONB, use canonical JSON
    # only for local equality. DB snapshot approvals use state::text SHA-256
    # computed in PostgreSQL, NOT this Python representation.
    import json
    return hashlib.sha256(json.dumps(state,sort_keys=True,separators=(",",":"),
                                      ensure_ascii=False).encode("utf-8")).hexdigest()


def require_approval(args) -> None:
    if not args.apply:
        return
    pairs=(("source_version",1),("target_version",1),
           ("expected_attachments",1),("expected_total_bytes",1))
    for key,minimum in pairs:
        value=getattr(args,key,None)
        if type(value) is not int or value<minimum:
            raise TransferBlocked("Missing or invalid frozen snapshot dimensions")
    if not all((args.confirm_frozen_writes,args.approved_change_ref.strip(),
                args.verified_restore_ref.strip(),args.manifest,
                args.source_root,args.target_root)):
        raise TransferBlocked("Missing approved restore, write freeze or private Storage file proof")
    for key in ("source_sha256","target_sha256"):
        value=getattr(args,key,"")
        if re.fullmatch(r"[0-9a-fA-F]{64}",value) is None:
            raise TransferBlocked("Missing frozen database JSONB checksum")


def build_parser():
    p=argparse.ArgumentParser(description="CSB Klarin private data delta: READ ONLY unless gated --apply")
    p.add_argument("--apply",action="store_true")
    p.add_argument("--source-version",type=int)
    p.add_argument("--target-version",type=int)
    p.add_argument("--source-sha256",default="")
    p.add_argument("--target-sha256",default="")
    p.add_argument("--expected-attachments",type=int)
    p.add_argument("--expected-total-bytes",type=int)
    p.add_argument("--approved-change-ref",default="")
    p.add_argument("--verified-restore-ref",default="")
    p.add_argument("--confirm-frozen-writes",action="store_true")
    p.add_argument("--manifest",default="")
    p.add_argument("--source-root",default="")
    p.add_argument("--target-root",default="")
    return p


def check_tenant_permissions(cursor):
    for table in TABLES:
        name=TARGET_SCHEMA+"."+table
        cursor.execute("SELECT to_regclass(%s)",(name,))
        if cursor.fetchone()["to_regclass"] is None:
            raise TransferBlocked("Target CSB tenant table missing")
        cursor.execute("SELECT relrowsecurity FROM pg_class WHERE oid=%s::regclass",(name,))
        if not cursor.fetchone()["relrowsecurity"]:
            raise TransferBlocked("Target CSB tenant RLS disabled")
        for role in ("anon","authenticated","gpro_gpp_stock"):
            for privilege in ("SELECT","INSERT","UPDATE","DELETE"):
                cursor.execute("SELECT has_table_privilege(%s,%s,%s) AS yes",
                               (role,name,privilege))
                if cursor.fetchone()["yes"]:
                    raise TransferBlocked("Cross-tenant or browser direct table privilege")
        for privilege in ("SELECT","INSERT","UPDATE","DELETE"):
            cursor.execute("SELECT has_table_privilege('service_role',%s,%s) AS yes",
                           (name,privilege))
            if not cursor.fetchone()["yes"]:
                raise TransferBlocked("Server role CRUD incomplete")
    cursor.execute("SELECT public FROM storage.buckets WHERE id=%s",(TARGET_BUCKET,))
    bucket=cursor.fetchone()
    if bucket is None or bucket["public"] is not False:
        raise TransferBlocked("Target CSB private Storage bucket unavailable")


def read_app(cursor,schema):
    cursor.execute(
        f"SELECT state,version,updated_at FROM {schema}.klarin_stock_claim_app_state "
        "WHERE workspace_key=%s", (STATE_KEY,))
    row=cursor.fetchone()
    if row is None or not isinstance(row["state"],dict):
        raise TransferBlocked("CSB claim state absent or invalid")
    return row


def read_attachments(cursor,schema):
    cursor.execute("SELECT "+",".join(ATTACH_COLUMNS)+" FROM "+
                   schema+".klarin_stock_claim_attachments ORDER BY id")
    return cursor.fetchall()


def object_inventory(cursor,bucket):
    cursor.execute("""
      SELECT name, COALESCE((metadata->>'size')::bigint,-1) AS size
      FROM storage.objects WHERE bucket_id=%s
    """,(bucket,))
    values=cursor.fetchall()
    result={row["name"]:row["size"] for row in values}
    if len(result)!=len(values):
        raise TransferBlocked("Storage has duplicate object names")
    return result


def assert_original_objects(source_meta,source_objects,target_objects):
    expected={row["storage_path"]:int(row["size_bytes"]) for row in source_meta}
    if len(expected)!=len(source_meta):
        raise TransferBlocked("Duplicate source Storage paths")
    if expected!=source_objects:
        raise TransferBlocked("Source Storage object metadata does not match claim rows")
    if expected!=target_objects:
        raise TransferBlocked("Target Storage files missing, extra or of wrong size")
    if any(row["data_base64"] not in ("",None) for row in source_meta):
        raise TransferBlocked("Inline file bytes are not supported by this transfer")
    return expected


def check_frozen_sha(cursor,schema,expected_sha):
    cursor.execute(
        f"SELECT encode(sha256(convert_to(state::text,'UTF8')),'hex') AS digest "
        f"FROM {schema}.klarin_stock_claim_app_state WHERE workspace_key=%s",
        (STATE_KEY,))
    row=cursor.fetchone()
    if row is None or row["digest"].lower()!=expected_sha.lower():
        raise TransferBlocked("Live source/target claim state differs from frozen checksum")


def attachment_record_equal(source,target):
    return all(source[k]==target[k] for k in ATTACH_COLUMNS
               if k!="storage_migrated_at")


def verify_private_byte_proof(args,meta):
    from csb_klarin_storage_byte_audit import (
        private_manifest, audit, ByteAuditBlocked,
    )
    manifest=private_manifest(Path(args.manifest))
    by_id={row["id"]:row for row in meta}
    if len(manifest)!=len(by_id):
        raise TransferBlocked("Private byte manifest count differs from source DB")
    for entry in manifest:
        source=by_id.get(entry["id"])
        if source is None:
            raise TransferBlocked("Private proof references an unrecognized claim attachment")
        for key in ("owner_type","owner_id","file_name","mime_type","size_bytes","storage_path"):
            if source[key]!=entry.get(key):
                raise TransferBlocked("Private byte proof and source DB metadata disagree")
        if not entry.get("expected_sha256"):
            raise TransferBlocked("Every original file needs independently recorded SHA-256 proof")
        if entry["_target_path"]!=entry["_source_path"]:
            raise TransferBlocked("Target Storage path remapping needs separate approved migration")
    try:
        report=audit(manifest,Path(args.source_root),Path(args.target_root),
                     expected_objects=args.expected_attachments,
                     expected_bytes=args.expected_total_bytes)
    except ByteAuditBlocked:
        raise TransferBlocked("Private Storage byte audit failed") from None
    if not report["source_target_bytes_equal"] or (
        report["source_expected_sha256_proofs_verified"]!=args.expected_attachments
    ):
        raise TransferBlocked("Private Storage SHA-256 proof incomplete")


def merged_state(source,target):
    from csb_klarin_claim_delta_plan import (
        merged_state_from_verified_subset, DeltaBlocked,
    )
    try:
        return merged_state_from_verified_subset(
            {"version":source["version"],"state":source["state"]},
            {"version":target["version"],"state":target["state"]})
    except DeltaBlocked:
        raise TransferBlocked("Claim business IDs or contents conflict") from None


def main() -> int:
    args=build_parser().parse_args()
    try:
        require_approval(args)
        source_dsn=os.environ.get("GPRO_CSB_KLARIN_SOURCE_DSN","")
        target_dsn=os.environ.get("GPRO_CSB_KLARIN_TARGET_DSN","")
        require_operator_url(source_dsn,SOURCE_REF)
        require_operator_url(target_dsn,TARGET_REF)
    except TransferBlocked:
        print("NO-GO: missing private operator credentials or signed cutover approval",file=sys.stderr)
        return 2

    try:
        import psycopg
        from psycopg.types.json import Jsonb
        from psycopg.rows import dict_row
        from csb_klarin_claim_delta_plan import plan, DeltaBlocked
    except ImportError:
        print("NO-GO: reviewed Python runtime and psycopg3 dependencies required",file=sys.stderr)
        return 2

    source=target=None
    try:
        source=psycopg.connect(source_dsn,sslmode="require",connect_timeout=12,
                               autocommit=True,row_factory=dict_row)
        target=psycopg.connect(target_dsn,sslmode="require",connect_timeout=12,
                               autocommit=True,row_factory=dict_row)
        with source.cursor() as sc,target.cursor() as tc:
            sc.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            tc.execute("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE" if args.apply
                       else "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            if args.apply:
                tc.execute("SELECT current_user AS role")
                if tc.fetchone()["role"]!="postgres":
                    raise TransferBlocked("Target write must use approved postgres operator role")
                tc.execute("LOCK TABLE csb_klarin.klarin_stock_claim_attachments IN SHARE ROW EXCLUSIVE MODE")
            check_tenant_permissions(tc)
            source_state=read_app(sc,SOURCE_SCHEMA)
            target_state=read_app(tc,TARGET_SCHEMA)
            sc.execute("SELECT version FROM public.klarin_realtime_signal WHERE workspace_key=%s",
                       (STATE_KEY,))
            source_signal=sc.fetchone()
            tc.execute("SELECT version FROM csb_klarin.klarin_realtime_signal WHERE workspace_key=%s "+
                       ("FOR UPDATE" if args.apply else ""), (STATE_KEY,))
            target_signal=tc.fetchone()
            if (source_signal is None or target_signal is None or
                source_signal["version"]!=source_state["version"] or
                target_signal["version"]!=target_state["version"]):
                raise TransferBlocked("Realtime signal and claim state versions do not match")
            source_meta=read_attachments(sc,SOURCE_SCHEMA)
            target_meta=read_attachments(tc,TARGET_SCHEMA)
            summary=plan(
                {"version":source_state["version"],"state":source_state["state"]},
                {"version":target_state["version"],"state":target_state["state"]},
                source_meta,target_meta,
            )
            if args.source_version is not None and source_state["version"]!=args.source_version:
                raise TransferBlocked("Source claim state version changed")
            if args.target_version is not None and target_state["version"]!=args.target_version:
                raise TransferBlocked("Target claim state version changed")
            if args.expected_attachments is not None and len(source_meta)!=args.expected_attachments:
                raise TransferBlocked("Legacy claim attachment count differs from approved inventory")
            if args.expected_total_bytes is not None and sum(int(x["size_bytes"]) for x in source_meta)!=args.expected_total_bytes:
                raise TransferBlocked("Legacy claim attachment total bytes changed")
            print(
                "READ ONLY snapshot: source_ver="+str(source_state["version"])+
                " target_ver="+str(target_state["version"])+
                " claims_missing="+str(summary["source_only_entries"]["monitoringKlaim"])+
                " batches_missing="+str(summary["source_only_entries"]["uploadBatches"])+
                " audit_missing="+str(summary["source_only_entries"]["auditLogs"])+
                " attachments_missing="+str(summary["missing_attachment_metadata"])
            )
            if not args.apply:
                tc.execute("ROLLBACK")
                sc.execute("ROLLBACK")
                print("DRY RUN: NO database writes, NO Storage transfer")
                return 0

            check_frozen_sha(sc,SOURCE_SCHEMA,args.source_sha256)
            check_frozen_sha(tc,TARGET_SCHEMA,args.target_sha256)
            expected_source=object_inventory(sc,SOURCE_BUCKET)
            expected_target=object_inventory(tc,TARGET_BUCKET)
            assert_original_objects(source_meta,expected_source,expected_target)
            verify_private_byte_proof(args,source_meta)
            target_by_id={row["id"]:row for row in target_meta}
            for entry in source_meta:
                existing=target_by_id.get(entry["id"])
                if existing is not None:
                    if not attachment_record_equal(entry,existing):
                        raise TransferBlocked("Existing claim attachment metadata conflict")
                    continue
                values=[
                    entry[col] if col!="storage_migrated_at" else None
                    for col in ATTACH_COLUMNS
                ]
                values[-1]=None  # Target migration timestamp is set server side.
                sql_cols=",".join(ATTACH_COLUMNS[:-1])+",storage_migrated_at"
                placeholders=",".join(["%s"]*(len(ATTACH_COLUMNS)-1))+",now()"
                tc.execute(
                    "INSERT INTO csb_klarin.klarin_stock_claim_attachments ("+
                    sql_cols+") VALUES ("+placeholders+")",
                    values[:-1],
                )
            merged=merged_state(source_state,target_state)
            tc.execute("""
                UPDATE csb_klarin.klarin_stock_claim_app_state
                   SET state=%s::jsonb,version=%s,updated_by='GPRO_TWO_BASE_MIGRATION',
                       updated_at=now()
                 WHERE workspace_key=%s AND version=%s AND state=%s::jsonb
                 RETURNING version
            """,(Jsonb(merged),source_state["version"],STATE_KEY,target_state["version"],
                 Jsonb(target_state["state"])))
            updated=tc.fetchone()
            if updated is None or updated["version"]!=source_state["version"]:
                raise TransferBlocked("Optimistic version/CAS rejected state write")
            tc.execute("""
                UPDATE csb_klarin.klarin_realtime_signal
                   SET version=%s,updated_at=now()
                 WHERE workspace_key=%s AND version=%s
                 RETURNING version
            """,(source_state["version"],STATE_KEY,target_state["version"]))
            signal=tc.fetchone()
            if signal is None or signal["version"]!=source_state["version"]:
                raise TransferBlocked("Optimistic realtime signal CAS rejected")
            tc.execute("SELECT state,version FROM csb_klarin.klarin_stock_claim_app_state WHERE workspace_key=%s",
                       (STATE_KEY,))
            end=tc.fetchone()
            if end["state"]!=source_state["state"] or end["version"]!=source_state["version"]:
                raise TransferBlocked("Source and target claim JSON state diverged")
            completed=read_attachments(tc,TARGET_SCHEMA)
            if len(completed)!=len(source_meta):
                raise TransferBlocked("Attachment target metadata incomplete")
            final_map={row["id"]:row for row in completed}
            if any(row["id"] not in final_map or
                   not attachment_record_equal(row,final_map[row["id"]]) for row in source_meta):
                raise TransferBlocked("Final claim attachment metadata conflicts")
            tc.execute("COMMIT")
            sc.execute("ROLLBACK")
            print("Verified target claim state, audit entries and attachment metadata committed. "+
                  "Storage byte proof was verified offline; app E2E and full cutover remain separate.")
            return 0
    except Exception as exc:
        if target:
            try: target.execute("ROLLBACK")
            except Exception: pass
        if source:
            try: source.execute("ROLLBACK")
            except Exception: pass
        print("NO-GO: "+(str(exc) if isinstance(exc,TransferBlocked) else type(exc).__name__),file=sys.stderr)
        return 2
    finally:
        if target: target.close()
        if source: source.close()


if __name__=="__main__":
    raise SystemExit(main())
