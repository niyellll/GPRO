#!/usr/bin/env python3
"""GPP Pusat state/attachment reconciliation to the existing Klarin BASE.

Default: NO NETWORK / NO WRITE. --live: two pinned read-only snapshots.
--apply: SERIALIZABLE, owner-attested, private original/target byte evidence.
Never modify GPP Cabang, browser roles, existing target user/session rows,
original Storage objects, or other tenant schemas. Not production cutover.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys

from csb_klarin_state_transfer_guarded import (
    require_operator_url, object_inventory, assert_original_objects,
    TransferBlocked,
)
from csb_klarin_claim_delta_plan import (
    plan, merged_state_from_verified_subset, DeltaBlocked,
)
from csb_klarin_storage_byte_audit import private_manifest, audit, ByteAuditBlocked

SOURCE_REF="aupbqpdxiqulxcxeewri"
TARGET_REF="numlkqppirrxfwdhazja"
SOURCE_SCHEMA="public"
TARGET_SCHEMA="gpp_stock"
SOURCE_BUCKET="gpp-klarin-attachments"
TARGET_BUCKET="gpro-gpp-private-attachments"
SOURCE_DSN_ENV="GPRO_GPP_STOCK_SOURCE_DSN"
TARGET_DSN_ENV="GPRO_GPP_STOCK_TARGET_DSN"
WORKSPACE="gpp_pusat"
UNCHANGED_WORKSPACE="gpp_cabang"
HASH=re.compile(r"[0-9a-fA-F]{64}\Z")
COLUMNS=(
    "id","workspace_key","owner_type","owner_id","file_name",
    "mime_type","size_bytes","data_base64","uploaded_by",
    "created_at","storage_path","storage_migrated_at",
)


class GppStateBlocked(ValueError):
    pass


def parser():
    p=argparse.ArgumentParser(description="GPP state migration: NO NETWORK by default")
    p.add_argument("--live",action="store_true",help="Real read-only census with pinned DSNs")
    p.add_argument("--apply",action="store_true",help="Protected serializable transaction")
    p.add_argument("--approved-change-ref",default="")
    p.add_argument("--verified-restore-ref",default="")
    p.add_argument("--confirm-frozen-writes",action="store_true")
    p.add_argument("--source-version",type=int,default=0)
    p.add_argument("--target-version",type=int,default=0)
    p.add_argument("--source-sha256",default="")
    p.add_argument("--target-sha256",default="")
    p.add_argument("--cabang-version",type=int,default=0)
    p.add_argument("--cabang-sha256",default="")
    p.add_argument("--expected-attachments",type=int,default=0)
    p.add_argument("--expected-total-bytes",type=int,default=0)
    p.add_argument("--manifest",default="")
    p.add_argument("--source-root",default="")
    p.add_argument("--target-root",default="")
    return p


def approval(a):
    if not a.apply:
        return
    if not (a.live and a.approved_change_ref.strip()
            and a.verified_restore_ref.strip() and a.confirm_frozen_writes
            and a.source_version>=1 and a.target_version>=1
            and a.cabang_version>=1 and a.expected_attachments>=1
            and a.expected_total_bytes>=1 and a.manifest and a.source_root
            and a.target_root and all(HASH.fullmatch(x or "") for x in (
                a.source_sha256,a.target_sha256,a.cabang_sha256))):
        raise GppStateBlocked("Verified restore, frozen snapshot and private byte proof required")


def read_workspace(cur, schema, workspace, *, lock=False):
    sql=(f"SELECT state,version,updated_at FROM {schema}.klarin_stock_claim_app_state "
         "WHERE workspace_key=%s"+(" FOR UPDATE" if lock else ""))
    cur.execute(sql,(workspace,))
    row=cur.fetchone()
    if row is None or not isinstance(row["state"],dict) or type(row["version"]) is not int:
        raise GppStateBlocked("Workspace claim state missing or malformed")
    return row


def state_sha(cur,schema,workspace):
    cur.execute(f"""
      SELECT encode(sha256(convert_to(state::text,'UTF8')),'hex') AS checksum
      FROM {schema}.klarin_stock_claim_app_state WHERE workspace_key=%s
    """,(workspace,))
    row=cur.fetchone()
    if row is None:
        raise GppStateBlocked("Frozen workspace digest unavailable")
    return row["checksum"]


def cabang_guard(sc,tc,a):
    sc.execute("SELECT version FROM public.klarin_stock_claim_app_state WHERE workspace_key=%s",
               (UNCHANGED_WORKSPACE,))
    tc.execute("SELECT version FROM gpp_stock.klarin_stock_claim_app_state WHERE workspace_key=%s",
               (UNCHANGED_WORKSPACE,))
    x,y=sc.fetchone(),tc.fetchone()
    if (x is None or y is None or x["version"]!=y["version"]
            or state_sha(sc,SOURCE_SCHEMA,UNCHANGED_WORKSPACE)
            != state_sha(tc,TARGET_SCHEMA,UNCHANGED_WORKSPACE)):
        raise GppStateBlocked("GPP Cabang already differs or cannot be preserved")
    if a.apply and (x["version"]!=a.cabang_version or
            state_sha(tc,TARGET_SCHEMA,UNCHANGED_WORKSPACE)!=a.cabang_sha256.lower()):
        raise GppStateBlocked("Frozen Cabang snapshot changed")


def attachment_rows(cur,schema):
    cur.execute("SELECT "+",".join(COLUMNS)+f" FROM {schema}.klarin_stock_claim_attachments "
                "ORDER BY id")
    rows=cur.fetchall()
    if any(r["workspace_key"]!=WORKSPACE or r["owner_type"]!="klaim" for r in rows):
        raise GppStateBlocked("Cross-workspace or unsupported attachment detected")
    if len({r["id"] for r in rows})!=len(rows):
        raise GppStateBlocked("Duplicate attachment identity")
    return rows


def acl_guard(tc):
    for table in ("klarin_stock_claim_app_state","klarin_stock_claim_attachments"):
        name=TARGET_SCHEMA+"."+table
        tc.execute("SELECT relrowsecurity FROM pg_class WHERE oid=%s::regclass",(name,))
        row=tc.fetchone()
        if row is None or not row["relrowsecurity"]:
            raise GppStateBlocked("GPP tenant RLS must stay enabled")
        for role in ("anon","authenticated","gpro_csb_klarin"):
            for privilege in ("SELECT","INSERT","UPDATE","DELETE"):
                tc.execute("SELECT has_table_privilege(%s,%s,%s) AS ok",
                           (role,name,privilege))
                if tc.fetchone()["ok"]:
                    raise GppStateBlocked("Cross-tenant or browser SQL privileges detected")
        for privilege in ("SELECT","INSERT","UPDATE","DELETE"):
            tc.execute("SELECT has_table_privilege('service_role',%s,%s) AS ok",
                       (name,privilege))
            if not tc.fetchone()["ok"]:
                raise GppStateBlocked("Approved server-side writer permission missing")
    tc.execute("SELECT public,file_size_limit FROM storage.buckets WHERE id=%s",
               (TARGET_BUCKET,))
    bucket=tc.fetchone()
    if bucket is None or bucket["public"] is not False or bucket["file_size_limit"]!=52428800:
        raise GppStateBlocked("GPP destination dedicated private bucket unavailable")


def validate_manifest(a, source_meta):
    m=private_manifest(Path(a.manifest))
    if len(m)!=len(source_meta) or len(m)!=a.expected_attachments:
        raise GppStateBlocked("Original private manifest incomplete")
    by_id={r["id"]:r for r in source_meta}
    if len(by_id)!=len(source_meta):
        raise GppStateBlocked("Duplicate original metadata ID")
    for e in m:
        row=by_id.get(e["id"])
        if row is None or e.get("workspace_key")!=WORKSPACE:
            raise GppStateBlocked("Private manifest cross-workspace owner or UUID")
        for key in ("workspace_key","owner_type","owner_id","file_name","mime_type",
                    "size_bytes","storage_path"):
            if e[key]!=row[key]:
                raise GppStateBlocked("Frozen original file metadata changed")
        if not e.get("expected_sha256") or e["_source_path"]!=e["_target_path"]:
            raise GppStateBlocked("Original/target private byte proof incomplete")
    try:
        result=audit(m,Path(a.source_root),Path(a.target_root),
                     expected_objects=a.expected_attachments,
                     expected_bytes=a.expected_total_bytes)
    except ByteAuditBlocked:
        raise GppStateBlocked("Original/target file-byte SHA-256 proof failed") from None
    if not result["source_target_bytes_equal"] or (
            result["source_expected_sha256_proofs_verified"]!=a.expected_attachments):
        raise GppStateBlocked("Private file-byte hash parity not verified")


def metadata_matches(src,dst):
    return all(src[c]==dst[c] for c in COLUMNS if c!="storage_migrated_at")


def operate(a):
    approval(a)
    if not a.live and not a.apply:
        print("OFFLINE NO-NETWORK: no database or Storage operation permitted")
        return 0
    source_url=os.environ.get(SOURCE_DSN_ENV,"")
    target_url=os.environ.get(TARGET_DSN_ENV,"")
    require_operator_url(source_url,SOURCE_REF)
    require_operator_url(target_url,TARGET_REF)
    try:
        import psycopg
        from psycopg.types.json import Jsonb
        from psycopg.rows import dict_row
    except ImportError:
        raise GppStateBlocked("Private operator requires psycopg3") from None
    source=target=None
    try:
        source=psycopg.connect(source_url,sslmode="require",connect_timeout=12,
                               autocommit=True,row_factory=dict_row)
        target=psycopg.connect(target_url,sslmode="require",connect_timeout=12,
                               autocommit=True,row_factory=dict_row)
        with source.cursor() as sc,target.cursor() as tc:
            sc.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            tc.execute("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE" if a.apply
                       else "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            if a.apply:
                tc.execute("SELECT current_user AS role")
                if tc.fetchone()["role"]!="postgres":
                    raise GppStateBlocked("Owner-only GPP target transaction required")
                tc.execute("LOCK TABLE gpp_stock.klarin_stock_claim_attachments IN SHARE ROW EXCLUSIVE MODE")
            acl_guard(tc)
            cabang_guard(sc,tc,a)
            source_state=read_workspace(sc,SOURCE_SCHEMA,WORKSPACE)
            target_state=read_workspace(tc,TARGET_SCHEMA,WORKSPACE,lock=a.apply)
            source_meta=attachment_rows(sc,SOURCE_SCHEMA)
            target_meta=attachment_rows(tc,TARGET_SCHEMA)
            summary=plan(
                {"version":source_state["version"],"state":source_state["state"]},
                {"version":target_state["version"],"state":target_state["state"]},
                source_meta,target_meta)
            if a.apply:
                if (source_state["version"]!=a.source_version
                    or target_state["version"]!=a.target_version
                    or state_sha(sc,SOURCE_SCHEMA,WORKSPACE)!=a.source_sha256.lower()
                    or state_sha(tc,TARGET_SCHEMA,WORKSPACE)!=a.target_sha256.lower()
                    or len(source_meta)!=a.expected_attachments
                    or sum(r["size_bytes"] for r in source_meta)!=a.expected_total_bytes):
                    raise GppStateBlocked("Frozen GPP source/target count or state drift")
                source_objects=object_inventory(sc,SOURCE_BUCKET)
                target_objects=object_inventory(tc,TARGET_BUCKET)
                assert_original_objects(source_meta,source_objects,target_objects)
                validate_manifest(a,source_meta)
            else:
                tc.execute("ROLLBACK")
                sc.execute("ROLLBACK")
                print("READ ONLY GPP: source_ver="+str(source_state["version"])+
                      " target_ver="+str(target_state["version"])+
                      " claims_missing="+str(summary["source_only_entries"]["monitoringKlaim"])+
                      " audit_missing="+str(summary["source_only_entries"]["auditLogs"])+
                      " batches_missing="+str(summary["source_only_entries"]["uploadBatches"])+
                      " attachments_missing="+str(summary["missing_attachment_metadata"]))
                return 0
            target_ids={r["id"]:r for r in target_meta}
            for row in source_meta:
                existing=target_ids.get(row["id"])
                if existing:
                    if not metadata_matches(row,existing):
                        raise GppStateBlocked("Conflicting target attachment identity")
                    continue
                values=[row[k] for k in COLUMNS[:-1]]
                cols=",".join(COLUMNS)
                tc.execute(
                    "INSERT INTO gpp_stock.klarin_stock_claim_attachments ("+cols+
                    ") VALUES ("+",".join(["%s"]*(len(COLUMNS)-1))+",now())",
                    values)
            merged=merged_state_from_verified_subset(
                {"version":source_state["version"],"state":source_state["state"]},
                {"version":target_state["version"],"state":target_state["state"]})
            tc.execute("""
                UPDATE gpp_stock.klarin_stock_claim_app_state
                SET state=%s::jsonb, version=%s,
                    updated_by='GPRO_TWO_BASE_MIGRATION', updated_at=now()
                WHERE workspace_key=%s AND version=%s AND state=%s::jsonb
                RETURNING version
            """,(Jsonb(merged),source_state["version"],WORKSPACE,
                 target_state["version"],Jsonb(target_state["state"])))
            result=tc.fetchone()
            if result is None or result["version"]!=source_state["version"]:
                raise GppStateBlocked("Optimistic GPP Pusat CAS rejected")
            end=read_workspace(tc,TARGET_SCHEMA,WORKSPACE)
            if end["state"]!=source_state["state"] or end["version"]!=source_state["version"]:
                raise GppStateBlocked("Final GPP Pusat claim state differs")
            cabang_guard(sc,tc,a)
            final_meta=attachment_rows(tc,TARGET_SCHEMA)
            final_ids={r["id"]:r for r in final_meta}
            if len(final_ids)!=len(source_meta) or any(
                    row["id"] not in final_ids or
                    not metadata_matches(row,final_ids[row["id"]]) for row in source_meta):
                raise GppStateBlocked("GPP final attachment metadata not reconciled")
            tc.execute("COMMIT")
            sc.execute("ROLLBACK")
            print("COMMITTED: GPP Pusat claim and metadata CAS only. "+
                  "GPP Cabang retained; app authenticated E2E/cutover still NO-GO.")
            return 0
    except Exception:
        for c in (target,source):
            if c:
                try: c.execute("ROLLBACK")
                except Exception: pass
        raise GppStateBlocked("GPP guarded state transaction was rejected") from None
    finally:
        if target: target.close()
        if source: source.close()


def main():
    try:
        return operate(parser().parse_args())
    except Exception:
        print("NO-GO: GPP state restore, owner/role, frozen data, or private bytes failed",
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
