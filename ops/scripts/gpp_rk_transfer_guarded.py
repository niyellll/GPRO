#!/usr/bin/env python3
"""GPRO 7->2 DB: guarded GPP Pusat RK transfer. Default is READ-ONLY dry-run.

NEVER execute --apply before owner-approved full DB+Storage restore, true write
freeze, validated Preview role isolation, and production change authorization.
No customer records or passwords are embedded in this script or printed.
Requires Python 3.10+ and psycopg 3; DSNs only from secure process environment.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from urllib.parse import unquote, urlsplit

SOURCE_REF = "vmpurwykfzcmculnnjfw"
TARGET_REF = "fdhqidjltlihzdcbqfrd"
SOURCE_TABLE = "public.rekening_koran_working_lines_v439"
TARGET_TABLE = "gpp_piutang.rekening_koran_working_lines_v439"
PERIOD_TABLE = "gpp_piutang.rekening_koran_period_meta_v543"
# Only the 22 original source columns. The target has 3 additional optional fields.
COLUMNS = (
    "id", "bank_account_code", "bank_label", "tanggal", "tickmark",
    "reff", "keterangan", "debet", "kredit", "saldo", "saldo_present",
    "source_order", "checked", "no_akun", "lawan_transaksi", "referensi",
    "posisi", "is_active", "created_by", "updated_by", "created_at", "updated_at",
)
NEW_COLUMNS = ("matched_journal_no", "matched_source", "attachment_note")
# Digest always projects the exact 22 original source columns


def require_correct_project(dsn: str, expected_ref: str) -> None:
    """Reject wrong project and arbitrary host to avoid cross-tenant writes."""
    try:
        p = urlsplit(dsn)
        host = (p.hostname or "").lower()
        user = unquote(p.username or "")
        valid_direct = host == f"db.{expected_ref}.supabase.co"
        valid_pooler = host.endswith(".pooler.supabase.com") and user.endswith(f".{expected_ref}")
        if p.scheme not in ("postgresql", "postgres") or not (valid_direct or valid_pooler):
            raise ValueError("DSN project mismatch")
        if not p.password and not os.getenv("PGPASSWORD"):
            raise ValueError("no approved password source configured")
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Database endpoint verification failed for expected project {expected_ref}") from None


def fingerprint_query(schema: str) -> str:
    if schema not in ("public", "gpp_piutang"):
        raise ValueError("Unexpected database schema")
    projected = ", ".join("'" + column + "', t." + column for column in COLUMNS)
    return f"""
    WITH normalized AS (
      SELECT id, jsonb_build_object({projected})::text AS record_text,
             debet, kredit, tanggal
      FROM {schema}.rekening_koran_working_lines_v439 t
    )
    SELECT count(*)::bigint AS row_count,
           count(DISTINCT id)::bigint AS unique_ids,
           COALESCE(sum(debet),0) AS debit_total,
           COALESCE(sum(kredit),0) AS credit_total,
           min(tanggal) AS min_date,
           max(tanggal) AS max_date,
           encode(sha256(convert_to(COALESCE(string_agg(record_text, E'\\n' ORDER BY id),''),
                                   'UTF8')),'hex') AS content_sha256
    FROM normalized
    """


def prepare_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="GPP RK guarded transfer; dry-run by default")
    p.add_argument("--apply", action="store_true", help="Enable guarded transactional write only after all gates")
    p.add_argument("--expected-rows", type=int)
    p.add_argument("--expected-sha256", default="")
    p.add_argument("--approved-change-ref", default="")
    p.add_argument("--verified-restore-ref", default="")
    p.add_argument("--confirm-frozen-writes", action="store_true")
    return p


def check_approval(args: argparse.Namespace) -> None:
    if not args.apply:
        return
    if (not args.confirm_frozen_writes
        or not args.approved_change_ref.strip()
        or not args.verified_restore_ref.strip()
        or args.expected_rows is None or args.expected_rows < 1
        or not re.fullmatch(r"[0-9a-fA-F]{64}", args.expected_sha256)):
        raise ValueError(
            "NO-GO: --apply requires verified restore, approval, write freeze, "
            "expected count and exact SHA-256. See GPP Finance cutover runbook."
        )


def target_ready(cursor) -> None:
    cursor.execute("""
        SELECT to_regclass(%s) IS NOT NULL, to_regclass(%s) IS NOT NULL,
               to_regnamespace('gpp_piutang') IS NOT NULL
    """, (TARGET_TABLE, PERIOD_TABLE))
    table_ok, period_ok, schema_ok = cursor.fetchone()
    if not (table_ok and period_ok and schema_ok):
        raise ValueError("NO-GO: reviewed target RK/period schema not present; no change was made")
    cursor.execute("""
        SELECT c.relrowsecurity
        FROM pg_class c WHERE c.oid = %s::regclass
    """, (TARGET_TABLE,))
    if not cursor.fetchone()[0]:
        raise ValueError("NO-GO: target RK RLS disabled")
    cursor.execute("""
        SELECT array_agg(attname ORDER BY attnum)
        FROM pg_attribute
        WHERE attrelid = %s::regclass AND attnum > 0 AND NOT attisdropped
    """, (TARGET_TABLE,))
    actual = set(cursor.fetchone()[0] or [])
    if not set(COLUMNS + NEW_COLUMNS).issubset(actual):
        raise ValueError("NO-GO: target missing required original/compatibility columns")
    cursor.execute("""
        SELECT has_table_privilege('gpro_gpp_pusat',%s,'SELECT'),
               has_table_privilege('gpro_gpp_cabang',%s,'SELECT'),
               has_table_privilege('gpro_csb_finance',%s,'SELECT'),
               has_table_privilege('anon',%s,'SELECT'),
               has_table_privilege('authenticated',%s,'SELECT')
    """, (TARGET_TABLE,) * 5)
    own, cabang, csb, anonymous, authenticated = cursor.fetchone()
    if not own or cabang or csb or anonymous or authenticated:
        raise ValueError("NO-GO: GPP tenant table privileges unsafe")
    # PostgreSQL permission lists such as 'SELECT,INSERT' mean ANY privilege.
    # Check each required service grant and the period table independently.
    cursor.execute("""
        SELECT
          (SELECT relrowsecurity FROM pg_class WHERE oid=%s::regclass),
          has_table_privilege('gpro_gpp_pusat',%s,'SELECT'),
          has_table_privilege('gpro_gpp_cabang',%s,'SELECT'),
          has_table_privilege('gpro_csb_finance',%s,'SELECT'),
          has_table_privilege('anon',%s,'SELECT'),
          has_table_privilege('authenticated',%s,'SELECT')
    """, (PERIOD_TABLE,) * 6)
    period_rls, period_own, period_cabang, period_csb, period_anon, period_auth=cursor.fetchone()
    if not period_rls or not period_own or any((period_cabang,period_csb,period_anon,period_auth)):
        raise ValueError("NO-GO: GPP period metadata privacy or RLS unsafe")
    for table in (TARGET_TABLE,PERIOD_TABLE):
        for privilege in ("SELECT","INSERT","UPDATE","DELETE"):
            cursor.execute("SELECT has_table_privilege('service_role',%s,%s)",
                           (table,privilege))
            if not cursor.fetchone()[0]:
                raise ValueError("NO-GO: service_role lacks required "+privilege+" on GPP tenant table")


def require_no_multiple_active_business_signatures(cursor) -> None:
    """Only refuse ambiguous *active* bank lines, retaining archived history.

    GPP bank upload intentionally archives prior versions via is_active=false
    and imports new active UUIDs; archived duplicates are not double-active
    transactions. The app treats NULL is_active as active (COALESCE(...,true)).
    Never drop inactive rows or log raw business values.
    """
    cursor.execute("""
        WITH repeated_active AS (
          SELECT count(*) FILTER (WHERE coalesce(is_active,true))::bigint AS active_copies
          FROM public.rekening_koran_working_lines_v439
          GROUP BY bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo
          HAVING count(*) FILTER (WHERE coalesce(is_active,true)) > 1
        )
        SELECT count(*)::bigint AS multiple_active_groups,
               coalesce(sum(active_copies),0)::bigint AS implicated_active_rows
        FROM repeated_active
    """)
    groups, rows = cursor.fetchone()
    if groups or rows:
        raise ValueError(
            "NO-GO: source Rekening Koran has multiple ACTIVE rows with the "
            "same bank statement signature; preserve archived UUID history "
            "and investigate before moving data"
        )


def read_rows(cursor, table: str):
    if table not in (SOURCE_TABLE, TARGET_TABLE):
        raise ValueError("Unrecognized table")
    names = ", ".join(COLUMNS)
    cursor.execute(f"SELECT {names} FROM {table} ORDER BY id")
    return cursor.fetchall()


def main() -> int:
    args = prepare_parser().parse_args()
    try:
        check_approval(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    source_dsn = os.environ.get("GPRO_RK_SOURCE_DSN", "")
    target_dsn = os.environ.get("GPRO_RK_TARGET_DSN", "")
    require_correct_project(source_dsn, SOURCE_REF)
    require_correct_project(target_dsn, TARGET_REF)
    try:
        import psycopg  # type: ignore
    except ImportError:
        print("NO-GO: psycopg v3 is not installed in the approved operator environment", file=sys.stderr)
        return 2

    source = target = None
    try:
        source = psycopg.connect(source_dsn, sslmode="require", connect_timeout=12, autocommit=True)
        target = psycopg.connect(target_dsn, sslmode="require", connect_timeout=12, autocommit=True)
        with source.cursor() as sc, target.cursor() as tc:
            sc.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            tc.execute("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE")
            target_ready(tc)
            # Historical versions (is_active=false) must be transferred
            # intact. Reject only ambiguous multiple-active signatures.
            require_no_multiple_active_business_signatures(sc)
            sc.execute(fingerprint_query("public"))
            s = sc.fetchone()
            if s[0] != s[1]:
                raise ValueError("NO-GO: duplicate source UUIDs")
            if args.expected_rows is not None and s[0] != args.expected_rows:
                raise ValueError("NO-GO: source row count changed")
            if args.expected_sha256 and s[6].lower() != args.expected_sha256.lower():
                raise ValueError("NO-GO: source SHA-256 differs from approved snapshot")
            sc_rows = read_rows(sc, SOURCE_TABLE)
            dst_rows = read_rows(tc, TARGET_TABLE)
            source_map = {row[0]: row for row in sc_rows}
            target_map = {row[0]: row for row in dst_rows}
            conflicts = sum(1 for rid, row in target_map.items() if source_map.get(rid) != row)
            if conflicts:
                raise ValueError(f"NO-GO: {conflicts} target UUID conflicts or target-only rows")
            missing = [row for row in sc_rows if row[0] not in target_map]
            print(f"Source records: {len(sc_rows)}; matching target: {len(target_map)}; pending: {len(missing)}")
            print(f"Source SHA-256: {s[6]}")
            if not args.apply:
                tc.execute("ROLLBACK")
                sc.execute("ROLLBACK")
                print("DRY-RUN only: no rows inserted; no database changes")
                return 0
            tc.execute("SELECT current_user")
            if tc.fetchone()[0] != "postgres":
                raise ValueError("NO-GO: transfer requires authorized operator postgres connection")
            # The external source write freeze is an essential operational gate.
            tc.execute(f"LOCK TABLE {TARGET_TABLE} IN SHARE ROW EXCLUSIVE MODE")
            values = ", ".join(["%s"] * len(COLUMNS))
            names = ", ".join(COLUMNS)
            for row in missing:
                tc.execute(
                    f"INSERT INTO {TARGET_TABLE} ({names}) VALUES ({values})", row
                )
            tc.execute(fingerprint_query("gpp_piutang"))
            d = tc.fetchone()
            if d != s:
                raise ValueError("NO-GO: target fingerprint/count/amount/date mismatch; rollback")
            tc.execute("COMMIT")
            print(f"VERIFIED: inserted {len(missing)} missing RK records, transaction committed")
            try:
                sc.execute("ROLLBACK")
            except Exception:
                pass  # Source remains read-only; target commit has already succeeded.
            return 0
    except Exception as exc:
        if target:
            try: target.execute("ROLLBACK")
            except Exception: pass
        if source:
            try: source.execute("ROLLBACK")
            except Exception: pass
        # Never print connection strings, raw SQL, row data or credentials.
        print(f"NO-GO: {str(exc) if isinstance(exc, ValueError) else type(exc).__name__}", file=sys.stderr)
        return 2
    finally:
        if target:
            target.close()
        if source:
            source.close()


if __name__ == "__main__":
    raise SystemExit(main())
