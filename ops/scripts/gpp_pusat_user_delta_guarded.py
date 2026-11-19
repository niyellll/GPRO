#!/usr/bin/env python3
"""One-account GPP Pusat user recovery; live READ ONLY unless approved --apply.

SOURCE: legacy vmpurwykfzcmculnnjfw.public.users
TARGET: Finance BASE fdhqidjltlihzdcbqfrd.gpp_piutang.users

Preserve original credential/role and UUID privately, without printing values.
Never copy source active-session tokens. Instead increment auth_session_version
on the single missing target user, forcing a fresh application login.
Existing target users are never modified. No target cutover or project deletion.

Only run --apply after actual restored full PostgreSQL + physical Storage
backups for all seven Supabase projects, a signed source freeze and approved
per-tenant authentication test/rollback. Credentials are operator-held env.
"""
from __future__ import annotations
import argparse
import os
import re
import sys
from urllib.parse import parse_qs, unquote, urlsplit

SOURCE_REF = "vmpurwykfzcmculnnjfw"
TARGET_REF = "fdhqidjltlihzdcbqfrd"
SOURCE_TABLE = "public.users"
TARGET_TABLE = "gpp_piutang.users"
COLUMNS = ("id", "username", "password", "role", "created_at",
           "auth_session_version", "active_session_id",
           "active_session_expires_at", "updated_at")
STABLE_COLUMNS = ("id", "username", "password", "role", "created_at")
SOURCE_ENV = "GPRO_GPP_PUSAT_USER_SOURCE_DSN"
TARGET_ENV = "GPRO_GPP_PUSAT_USER_TARGET_DSN"
SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")

class UserTransferBlocked(ValueError):
    pass

def assert_owner_dsn(dsn: str, project_ref: str) -> None:
    if project_ref not in (SOURCE_REF, TARGET_REF):
        raise UserTransferBlocked("Unexpected database project")
    try:
        u = urlsplit(dsn)
        host = (u.hostname or "").lower()
        user = unquote(u.username or "")
        direct = (host == "db." + project_ref + ".supabase.co"
                  and user == "postgres" and u.port == 5432)
        pooler = (re.fullmatch(r"[a-z0-9-]+\.pooler\.supabase\.com", host)
                  and user == "postgres." + project_ref and u.port in (5432, 6543))
        query = parse_qs(u.query, keep_blank_values=True, strict_parsing=True) if u.query else {}
        ssl = query.get("sslmode", ["require"])
        if not (u.scheme in ("postgres", "postgresql") and (direct or pooler)
                and u.path == "/postgres" and not u.fragment
                and bool(u.password or os.environ.get("PGPASSWORD"))
                and set(query).issubset({"sslmode"}) and len(ssl) == 1
                and ssl[0] in ("require", "verify-full")):
            raise UserTransferBlocked("Owner connection, TLS or project mismatch")
    except (TypeError, ValueError):
        raise UserTransferBlocked("Owner connection, TLS or project mismatch") from None

def approval_gate(args) -> None:
    if not args.apply:
        return
    if not (args.confirm_frozen_writes
            and args.approved_change_ref.strip()
            and args.verified_restore_ref.strip()
            and args.confirm_session_reauthentication
            and args.expected_missing_role.strip()
            and args.expected_source_rows == 6
            and args.expected_target_rows == 5
            and SHA256.fullmatch(args.expected_source_sha256 or "")
            and SHA256.fullmatch(args.expected_target_sha256 or "")):
        raise UserTransferBlocked("Actual restored backup, freeze, both SHA256, login reauthentication signoff required")
    if any(x in args.expected_missing_role.casefold() for x in ("admin", "owner", "root", "superuser")):
        raise UserTransferBlocked("Privileged role requires a separate individual security review")

def stable_fingerprint_sql(table: str) -> str:
    if table not in (SOURCE_TABLE, TARGET_TABLE):
        raise UserTransferBlocked("Non-allowlisted user table")
    attrs = ",".join("'"+c+"',t."+c for c in STABLE_COLUMNS)
    return f"""WITH fingerprints AS (
        SELECT id,encode(sha256(convert_to(
          jsonb_build_object({attrs})::text,'UTF8')),'hex') AS digest
        FROM {table} t
    )
    SELECT count(*)::bigint,count(DISTINCT id)::bigint,
      encode(sha256(convert_to(
        coalesce(string_agg(digest,E'\\n' ORDER BY id),''),
        'UTF8')),'hex') AS content_sha
    FROM fingerprints"""

def read_users(cursor, table: str):
    if table not in (SOURCE_TABLE, TARGET_TABLE):
        raise UserTransferBlocked("Non-allowlisted user table")
    cursor.execute("SELECT "+",".join(COLUMNS)+" FROM "+table+" ORDER BY id")
    return cursor.fetchall()

def find_missing(source_rows, target_rows):
    src = {row[0]: row for row in source_rows}
    dst = {row[0]: row for row in target_rows}
    if (len(src) != len(source_rows) or len(dst) != len(target_rows)
        or len({row[1] for row in source_rows}) != len(source_rows)
        or len({row[1] for row in target_rows}) != len(target_rows)):
        raise UserTransferBlocked("Duplicate UUID or username")
    for key, value in dst.items():
        if key not in src or value[:5] != src[key][:5]:
            raise UserTransferBlocked("Target-only identity or modified account credential/role")
    missing = [row for row in source_rows if row[0] not in dst]
    if len(missing) != 1:
        raise UserTransferBlocked("Expected exactly one source-only user, no more or fewer")
    user = missing[0]
    if (any(user[1] == row[1] for row in target_rows)
        or not user[1] or not user[2] or not user[3]
        or user[5] is None or user[5] < 0
        or user[5] >= 9223372036854775807
        or user[6] is not None or user[7] is not None):
        raise UserTransferBlocked("Missing account conflicts, has active session or invalid credential/version")
    return user

def target_ready(cursor) -> None:
    cursor.execute("SELECT relrowsecurity FROM pg_class WHERE oid=%s::regclass", (TARGET_TABLE,))
    row=cursor.fetchone()
    if not row or not row[0]:
        raise UserTransferBlocked("Target GPP users RLS missing")
    cursor.execute("""SELECT
        has_table_privilege('gpro_gpp_pusat',%s,'SELECT'),
        has_table_privilege('gpro_gpp_pusat',%s,'INSERT'),
        has_table_privilege('gpro_gpp_cabang',%s,'SELECT'),
        has_table_privilege('anon',%s,'SELECT'),
        has_table_privilege('authenticated',%s,'SELECT'),
        has_table_privilege('service_role',%s,'INSERT')
        """,(TARGET_TABLE,)*6)
    own_read,own_write,other_read,anon_read,auth_read,service_insert=cursor.fetchone()
    if not own_read or own_write or other_read or anon_read or auth_read or not service_insert:
        raise UserTransferBlocked("Target GPP users tenant access grants unsafe")
    cursor.execute("""SELECT column_name FROM information_schema.columns
                      WHERE table_schema='gpp_piutang' AND table_name='users'""")
    if not set(COLUMNS).issubset({r[0] for r in cursor.fetchall()}):
        raise UserTransferBlocked("Target GPP users schema changed")

def parser():
    p=argparse.ArgumentParser(description="GPP Pusat one-user non-destructive recovery; dry-run by default")
    p.add_argument("--apply",action="store_true")
    p.add_argument("--approved-change-ref",default="")
    p.add_argument("--verified-restore-ref",default="")
    p.add_argument("--confirm-frozen-writes",action="store_true")
    p.add_argument("--confirm-session-reauthentication",action="store_true")
    p.add_argument("--expected-missing-role",default="")
    p.add_argument("--expected-source-rows",type=int)
    p.add_argument("--expected-target-rows",type=int)
    p.add_argument("--expected-source-sha256",default="")
    p.add_argument("--expected-target-sha256",default="")
    return p

def main() -> int:
    args=parser().parse_args()
    try:
        approval_gate(args)
        source_dsn=os.environ.get(SOURCE_ENV,"")
        target_dsn=os.environ.get(TARGET_ENV,"")
        assert_owner_dsn(source_dsn,SOURCE_REF)
        assert_owner_dsn(target_dsn,TARGET_REF)
    except UserTransferBlocked:
        print("NO-GO: missing private operator credentials or approval proof",file=sys.stderr)
        return 2
    try:
        import psycopg
    except ImportError:
        print("NO-GO: psycopg3 required on isolated operator machine",file=sys.stderr)
        return 2
    source=target=None
    try:
        source=psycopg.connect(source_dsn,sslmode="require",connect_timeout=12,autocommit=True)
        target=psycopg.connect(target_dsn,sslmode="require",connect_timeout=12,autocommit=True)
        with source.cursor() as sc,target.cursor() as tc:
            sc.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            tc.execute("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE" if args.apply
                       else "BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
            if args.apply:
                tc.execute("SELECT current_user")
                if tc.fetchone()[0] != "postgres":
                    raise UserTransferBlocked("Only approved owner may stage missing user")
                tc.execute("LOCK TABLE gpp_piutang.users IN SHARE ROW EXCLUSIVE MODE")
            target_ready(tc)
            sc.execute(stable_fingerprint_sql(SOURCE_TABLE)); source_fingerprint=sc.fetchone()
            tc.execute(stable_fingerprint_sql(TARGET_TABLE)); target_fingerprint=tc.fetchone()
            if (source_fingerprint[0] != source_fingerprint[1]
                or target_fingerprint[0] != target_fingerprint[1]):
                raise UserTransferBlocked("User UUID integrity mismatch")
            if args.expected_source_rows is not None and source_fingerprint[0] != args.expected_source_rows:
                raise UserTransferBlocked("Frozen source user count changed")
            if args.expected_target_rows is not None and target_fingerprint[0] != args.expected_target_rows:
                raise UserTransferBlocked("Frozen target user count changed")
            if args.expected_source_sha256 and source_fingerprint[2].lower() != args.expected_source_sha256.lower():
                raise UserTransferBlocked("Frozen source identity digest changed")
            if args.expected_target_sha256 and target_fingerprint[2].lower() != args.expected_target_sha256.lower():
                raise UserTransferBlocked("Frozen target identity digest changed")
            source_rows=read_users(sc,SOURCE_TABLE)
            target_rows=read_users(tc,TARGET_TABLE)
            missing=find_missing(source_rows,target_rows)
            if args.apply and missing[3] != args.expected_missing_role:
                raise UserTransferBlocked("Missing account role no longer matches operator approval")
            print(f"GPP Pusat users source={len(source_rows)} target={len(target_rows)} missing=1")
            if not args.apply:
                tc.execute("ROLLBACK");sc.execute("ROLLBACK")
                print("READ ONLY: no user secrets, UUIDs or sessions printed")
                return 0
            # New login must not inherit an existing source session token.
            # Increment version to invalidate tokens created for the older source account.
            values=(missing[0],missing[1],missing[2],missing[3],missing[4],
                    missing[5]+1,None,None,missing[8])
            tc.execute("INSERT INTO gpp_piutang.users ("+",".join(COLUMNS)+") VALUES ("+
                       ",".join("%s" for _ in COLUMNS)+")",values)
            after=read_users(tc,TARGET_TABLE)
            expected_source={row[0]:row[:5] for row in source_rows}
            if (len(after)!=len(source_rows)
                or {row[0]:row[:5] for row in after} != expected_source
                or any(row not in after for row in target_rows)
                or next(r for r in after if r[0]==missing[0])[5]!=missing[5]+1):
                raise UserTransferBlocked("GPP target credential, role or existing user changed; rollback")
            tc.execute(stable_fingerprint_sql(TARGET_TABLE))
            if tc.fetchone() != source_fingerprint:
                raise UserTransferBlocked("Final user stable content fingerprint mismatch; rollback")
            tc.execute("COMMIT");sc.execute("ROLLBACK")
            print("GPP Pusat: one missing user staged, login reauthentication REQUIRED")
            return 0
    except Exception:
        for conn in (target,source):
            if conn:
                try:conn.execute("ROLLBACK")
                except Exception:pass
        print("NO-GO: GPP user delta authorization, conflict or transaction failed",file=sys.stderr)
        return 2
    finally:
        if target:target.close()
        if source:source.close()

if __name__=="__main__":
    raise SystemExit(main())
