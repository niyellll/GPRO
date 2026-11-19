#!/usr/bin/env python3
"""CSB Finance append-only audit-log recovery: DRY-RUN BY DEFAULT.

Transfers ONLY UUID-identical, source-only audit rows to csb_finance.audit_logs
after owner-approved full PostgreSQL + Storage restoration and a write freeze.
Does NOT truncate, overwrite, delete, or silently reconcile conflicting rows.
Python 3.10+ + psycopg3 needed for operator-only live execution.
No secrets, raw JSON audit data or private UUIDs are embedded or logged.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from urllib.parse import unquote, urlsplit

SOURCE_REF = "lmbvbgkqvidtkzxtvtpe"
TARGET_REF = "fdhqidjltlihzdcbqfrd"
SOURCE_TABLE = "public.audit_logs"
TARGET_TABLE = "csb_finance.audit_logs"
COLUMNS = (
    "id", "tabel", "record_id", "action", "old_data", "new_data",
    "user_id", "created_at", "source", "app", "version",
)
JSON_COLUMNS = {"old_data", "new_data"}


class AuditTransferBlocked(ValueError):
    pass


def assert_pinned_dsn(dsn: str, expected_ref: str) -> None:
    try:
        u = urlsplit(dsn)
        host = (u.hostname or "").lower()
        username = unquote(u.username or "")
        direct = host == "db." + expected_ref + ".supabase.co"
        pooler = host.endswith(".pooler.supabase.com") and username.endswith("." + expected_ref)
        if u.scheme not in ("postgres","postgresql") or not (direct or pooler):
            raise AuditTransferBlocked("Endpoint project or protocol not allowlisted")
        if not u.password and not os.environ.get("PGPASSWORD"):
            raise AuditTransferBlocked("Password must be supplied in protected process environment")
        if u.query and re.search(r"(?:^|&)sslmode=(?:disable|allow|prefer)(?:&|$)", u.query, re.I):
            raise AuditTransferBlocked("Insecure TLS setting")
    except (ValueError, TypeError):
        raise AuditTransferBlocked("Endpoint validation failed; expected pinned project") from None


def parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description="CSB Finance audit delta, source read-only; dry-run is default")
    p.add_argument("--apply",action="store_true",help="Commit approved delta, never without all safety gates")
    p.add_argument("--expected-source-rows",type=int)
    p.add_argument("--expected-target-rows",type=int)
    p.add_argument("--expected-source-sha256",default="")
    p.add_argument("--approved-change-ref",default="")
    p.add_argument("--verified-restore-ref",default="")
    p.add_argument("--confirm-frozen-writes",action="store_true")
    return p


def approval_gate(args) -> None:
    if not args.apply:
        return
    if (
        not args.confirm_frozen_writes
        or not args.approved_change_ref.strip()
        or not args.verified_restore_ref.strip()
        or args.expected_source_rows is None or args.expected_source_rows < 1
        or args.expected_target_rows is None or args.expected_target_rows < 0
        or re.fullmatch("[0-9a-fA-F]{64}",args.expected_source_sha256) is None
    ):
        raise AuditTransferBlocked(
            "NO-GO: explicit restored-backup proof, signed change, frozen source, "
            "source+target counts and matching SHA-256 required"
        )


def fingerprint_sql(table: str) -> str:
    if table not in (SOURCE_TABLE,TARGET_TABLE):
        raise AuditTransferBlocked("Unexpected audit table")
    return f"""
    WITH entries AS (
      SELECT id, encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') AS row_sha
        FROM {table} t
    )
    SELECT count(*)::bigint, count(DISTINCT id)::bigint,
      encode(sha256(convert_to(
        coalesce(string_agg(row_sha,E'\\n' ORDER BY id),''),
        'UTF8')),'hex') AS source_set_sha
    FROM entries
    """


def target_ready(c) -> None:
    c.execute("SELECT to_regclass(%s) IS NOT NULL", (TARGET_TABLE,))
    if not c.fetchone()[0]:
        raise AuditTransferBlocked("NO-GO: CSB Finance target audit table absent")
    c.execute("SELECT relrowsecurity FROM pg_class WHERE oid=%s::regclass",(TARGET_TABLE,))
    if not c.fetchone()[0]:
        raise AuditTransferBlocked("NO-GO: CSB tenant audit RLS disabled")
    c.execute("""SELECT array_agg(attname ORDER BY attnum) FROM pg_attribute
       WHERE attrelid=%s::regclass AND attnum>0 AND NOT attisdropped""",(TARGET_TABLE,))
    if not set(COLUMNS).issubset(set(c.fetchone()[0] or [])):
        raise AuditTransferBlocked("NO-GO: target audit column contract incomplete")
    # IMPORTANT: PostgreSQL comma-separated privilege lists are OR, not AND!
    # Check every grant separately; a bare SELECT cannot satisfy server DML.
    c.execute("""SELECT
      has_table_privilege('anon',%s,'SELECT'),
      has_table_privilege('anon',%s,'INSERT'),
      has_table_privilege('authenticated',%s,'SELECT'),
      has_table_privilege('authenticated',%s,'INSERT'),
      has_table_privilege('gpro_gpp_pusat',%s,'SELECT'),
      has_table_privilege('gpro_gpp_cabang',%s,'SELECT'),
      has_table_privilege('gpro_csb_finance',%s,'SELECT'),
      has_table_privilege('service_role',%s,'SELECT'),
      has_table_privilege('service_role',%s,'INSERT'),
      has_table_privilege('service_role',%s,'UPDATE'),
      has_table_privilege('service_role',%s,'DELETE')
      """,(TARGET_TABLE,)*11)
    an_read,an_write,auth_read,auth_write,gpp1,gpp2,csb,svc_read,svc_insert,svc_update,svc_delete=c.fetchone()
    if any((an_read,an_write,auth_read,auth_write,gpp1,gpp2)) or not csb or not all((svc_read,svc_insert,svc_update,svc_delete)):
        raise AuditTransferBlocked("NO-GO: audit table grants fail tenant isolation or server CRUD")


def rows(c,table: str):
    if table not in (SOURCE_TABLE,TARGET_TABLE):
        raise AuditTransferBlocked("Unexpected table")
    c.execute("SELECT "+",".join(COLUMNS)+" FROM "+table+" ORDER BY id")
    return c.fetchall()


def delta(source_rows, target_rows):
    source = {row[0]:row for row in source_rows}
    target = {row[0]:row for row in target_rows}
    if len(source)!=len(source_rows) or len(target)!=len(target_rows):
        raise AuditTransferBlocked("Duplicate UUID detected")
    if any(k not in source or source[k] != row for k,row in target.items()):
        raise AuditTransferBlocked("Target-only UUID or same UUID has modified content")
    return [row for row in source_rows if row[0] not in target]


def main() -> int:
    args=parser().parse_args()
    try:
        approval_gate(args)
        sd=os.environ.get("GPRO_CSB_AUDIT_SOURCE_DSN","")
        td=os.environ.get("GPRO_CSB_AUDIT_TARGET_DSN","")
        assert_pinned_dsn(sd,SOURCE_REF)
        assert_pinned_dsn(td,TARGET_REF)
    except AuditTransferBlocked:
        print("NO-GO: missing approval or pinned source/target credentials",file=sys.stderr)
        return 2

    try:
        import psycopg
        from psycopg.types.json import Jsonb
    except ImportError:
        print("NO-GO: install psycopg3 only in the approved isolated operator environment",file=sys.stderr)
        return 2

    source=target=None
    try:
        source=psycopg.connect(sd,sslmode="require",connect_timeout=12,autocommit=True)
        target=psycopg.connect(td,sslmode="require",connect_timeout=12,autocommit=True)
        with source.cursor() as sc,target.cursor() as tc:
            sc.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            tc.execute("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE" if args.apply
                       else "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            if args.apply:
                tc.execute("SELECT current_user")
                if tc.fetchone()[0]!="postgres":
                    raise AuditTransferBlocked("NO-GO: target requires authorized postgres operator")
                tc.execute("LOCK TABLE csb_finance.audit_logs IN SHARE ROW EXCLUSIVE MODE")
            target_ready(tc)
            sc.execute(fingerprint_sql(SOURCE_TABLE))
            source_fingerprint=sc.fetchone()
            if source_fingerprint[0]!=source_fingerprint[1]:
                raise AuditTransferBlocked("NO-GO: source UUIDs duplicate")
            if args.expected_source_rows is not None and source_fingerprint[0]!=args.expected_source_rows:
                raise AuditTransferBlocked("NO-GO: source row count changed")
            if args.expected_source_sha256 and source_fingerprint[2].lower()!=args.expected_source_sha256.lower():
                raise AuditTransferBlocked("NO-GO: source checksum differs from frozen approval")
            sc_rows=rows(sc,SOURCE_TABLE)
            tc_rows=rows(tc,TARGET_TABLE)
            if args.expected_target_rows is not None and len(tc_rows)!=args.expected_target_rows:
                raise AuditTransferBlocked("NO-GO: target initial row count changed")
            missing=delta(sc_rows,tc_rows)
            print(f"CSB Finance audit source={len(sc_rows)} target={len(tc_rows)} pending={len(missing)}")
            print(f"Source audit set SHA256: {source_fingerprint[2]}")
            if not args.apply:
                tc.execute("ROLLBACK")
                sc.execute("ROLLBACK")
                print("DRY-RUN ONLY: zero writes; source and target unchanged")
                return 0
            placeholders=", ".join("%s" for _ in COLUMNS)
            for row in missing:
                values=tuple(Jsonb(v) if COLUMNS[i] in JSON_COLUMNS and v is not None else v
                             for i,v in enumerate(row))
                tc.execute(
                    "INSERT INTO "+TARGET_TABLE+" ("+",".join(COLUMNS)+") VALUES ("+placeholders+")",
                    values,
                )
            tc.execute(fingerprint_sql(TARGET_TABLE))
            dest_fingerprint=tc.fetchone()
            if dest_fingerprint!=source_fingerprint:
                raise AuditTransferBlocked("NO-GO: final audit set SHA mismatch; rollback")
            tc.execute("COMMIT")
            sc.execute("ROLLBACK")
            print(f"VERIFIED: inserted {len(missing)} immutable audit rows into CSB Finance target")
            return 0
    except Exception as exc:
        if target:
            try: target.execute("ROLLBACK")
            except Exception: pass
        if source:
            try: source.execute("ROLLBACK")
            except Exception: pass
        print("NO-GO: "+(str(exc) if isinstance(exc,AuditTransferBlocked) else type(exc).__name__),file=sys.stderr)
        return 2
    finally:
        if target: target.close()
        if source: source.close()


if __name__=="__main__":
    raise SystemExit(main())
