#!/usr/bin/env python3
"""Seven-project to two-BASE read-only reconciliation gate.

DEFAULT: completely offline (no network, writes, or credentials).
--live: connect to seven specifically pinned PostgreSQL sources using operator
held environment DSNs, take seven REPEATABLE READ READ ONLY snapshots and
compare all common tenant tables using sorted SHA-256 of normalized JSONB rows.

No customer fields, database URLs, password hashes, file paths or individual
UUIDs are printed. This tool CANNOT prove physical Storage bytes, restore
success, business E2E or owner approval; its cutover_ready is ALWAYS false.
It cannot pause, delete, migrate, grant, or change any Supabase project.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from urllib.parse import parse_qs, unquote, urlsplit

PROJECTS = {
    "finance_base": ("fdhqidjltlihzdcbqfrd", "GPRO_BASE_FINANCE_PG_DSN"),
    "klarin_base": ("numlkqppirrxfwdhazja", "GPRO_BASE_KLARIN_PG_DSN"),
    "csb_finance_old": ("lmbvbgkqvidtkzxtvtpe", "GPRO_CSB_FINANCE_OLD_PG_DSN"),
    "gpp_pusat_old": ("vmpurwykfzcmculnnjfw", "GPRO_GPP_PUSAT_OLD_PG_DSN"),
    "gpp_cabang_old": ("loodbfjkskduzqfthxxi", "GPRO_GPP_CABANG_OLD_PG_DSN"),
    "csb_klarin_old": ("krwoiucqfcijmihnrlem", "GPRO_CSB_KLARIN_OLD_PG_DSN"),
    "gpp_stock_old": ("aupbqpdxiqulxcxeewri", "GPRO_GPP_STOCK_OLD_PG_DSN"),
}
# logical label, source connection key, target key, target schema, tenant role
TENANTS = (
    ("csb_finance", "csb_finance_old", "finance_base", "csb_finance", "gpro_csb_finance"),
    ("gpp_pusat", "gpp_pusat_old", "finance_base", "gpp_piutang", "gpro_gpp_pusat"),
    ("gpp_cabang", "gpp_cabang_old", "finance_base", "gpp_finance_cabang", "gpro_gpp_cabang"),
    ("csb_klarin", "csb_klarin_old", "klarin_base", "csb_klarin", "gpro_csb_klarin"),
    ("gpp_stock", "gpp_stock_old", "klarin_base", "gpp_stock", "gpro_gpp_stock"),
)
TRANSIENT_TABLES = frozenset(("login_rate_limits", "klarin_sessions"))
FINANCE_ROLES = ("gpro_csb_finance","gpro_gpp_pusat","gpro_gpp_cabang")
KLARIN_ROLES = ("gpro_csb_klarin","gpro_gpp_stock")
USER_SESSION_COLUMNS = frozenset((
    "active_session_id", "active_session_expires_at",
    "active_session_last_seen_at", "auth_session_version", "updated_at",
))
IDENT = re.compile(r"[a-z][a-z0-9_]*\Z")
POOLER = re.compile(r"[a-z0-9-]+\.pooler\.supabase\.com\Z")

class NoGo(ValueError):
    pass

def pinned_owner_dsn(dsn: str, project_ref: str) -> bool:
    if project_ref not in {ref for ref, _ in PROJECTS.values()}:
        raise NoGo("Unexpected Supabase project")
    try:
        u = urlsplit(dsn)
        host = (u.hostname or "").lower()
        username = unquote(u.username or "")
        direct = (host == "db." + project_ref + ".supabase.co"
                  and username == "postgres" and u.port == 5432)
        pooler = (bool(POOLER.fullmatch(host))
                  and username == "postgres." + project_ref
                  and u.port in (5432, 6543))
        query = parse_qs(u.query, keep_blank_values=True, strict_parsing=True) if u.query else {}
        modes = query.get("sslmode", ["require"])
        if not (u.scheme in ("postgresql", "postgres") and (direct or pooler)
                and u.path == "/postgres" and not u.fragment
                and bool(u.password or os.environ.get("PGPASSWORD"))
                and set(query).issubset({"sslmode"})
                and len(modes) == 1 and modes[0] in ("require", "verify-full")):
            raise NoGo("Project/owner/TLS restriction failed")
        return True
    except (TypeError, ValueError):
        raise NoGo("Project/owner/TLS restriction failed") from None

def sql_ident(value: str) -> str:
    if not isinstance(value, str) or not IDENT.fullmatch(value):
        raise NoGo("Unexpected SQL catalog identifier")
    return '"' + value + '"'

def normalized_row_sql(schema: str, table: str, removed: set[str] | frozenset[str]) -> str:
    quoted = sql_ident(schema) + "." + sql_ident(table)
    if any(not IDENT.fullmatch(col) for col in removed):
        raise NoGo("Unexpected column in SHA-256 projection")
    expr = "to_jsonb(t)"
    if removed:
        names = ",".join("'" + col + "'" for col in sorted(removed))
        expr = "(" + expr + " - ARRAY[" + names + "]::text[])"
    return f"""WITH rows AS (
       SELECT ({expr})::text AS payload FROM {quoted} t
    ), digests AS (
       SELECT encode(sha256(convert_to(payload,'UTF8')),'hex') AS rowhash
       FROM rows
    )
    SELECT count(*)::bigint, encode(sha256(convert_to(
      coalesce(string_agg(rowhash,E'\\n' ORDER BY rowhash),''),
      'UTF8')),'hex') AS fingerprint
    FROM digests"""

def table_catalog(cursor, schema: str) -> dict[str,set[str]]:
    sql_ident(schema)
    cursor.execute("""
      SELECT c.relname, a.attname
      FROM pg_class c
      JOIN pg_namespace n ON n.oid=c.relnamespace
      JOIN pg_attribute a ON a.attrelid=c.oid
      WHERE n.nspname=%s AND c.relkind='r' AND NOT c.relispartition
        AND a.attnum>0 AND NOT a.attisdropped
      ORDER BY c.relname,a.attnum
    """, (schema,))
    tables: dict[str,set[str]] = {}
    for table,column in cursor.fetchall():
        sql_ident(table)
        sql_ident(column)
        tables.setdefault(table,set()).add(column)
    if not tables or len(tables)>150:
        raise NoGo("Tenant table inventory empty or unexpectedly large")
    return tables

def classify_table(tenant: str, table: str, source_cols: set[str],
                   target_cols: set[str]) -> tuple[set[str],set[str],str]:
    if not source_cols.issubset(target_cols):
        return set(),set(),"SCHEMA_MISMATCH"
    shared_volatile = USER_SESSION_COLUMNS & source_cols if table == "users" else set()
    source_omit = set(shared_volatile)
    target_omit = (target_cols-source_cols) | shared_volatile
    classification = "TRANSIENT" if table in TRANSIENT_TABLES else "BUSINESS"
    return source_omit, target_omit, classification

def table_comparison(source_cursor,target_cursor,tenant: str,
                     source_schema: str,target_schema: str,table: str,
                     source_cols: set[str], target_cols: set[str]) -> dict:
    src_omit,dst_omit,kind = classify_table(tenant,table,source_cols,target_cols)
    if kind=="SCHEMA_MISMATCH":
        return {"table":table,"status":kind,"kind":"BUSINESS"}
    source_cursor.execute(normalized_row_sql(source_schema,table,src_omit))
    source_count,source_sha = source_cursor.fetchone()
    target_cursor.execute(normalized_row_sql(target_schema,table,dst_omit))
    target_count,target_sha = target_cursor.fetchone()
    return {
        "table":table, "kind":kind,
        "source_count":int(source_count), "target_count":int(target_count),
        "status":"MATCH" if source_count==target_count and source_sha==target_sha else "DRIFT",
    }

def inspect_tenant(source_cursor,target_cursor,tenant: str,
                   target_schema: str, tenant_role: str) -> dict:
    src=table_catalog(source_cursor,"public")
    dst=table_catalog(target_cursor,target_schema)
    missing_tables=sorted(set(src)-set(dst))
    results=[table_comparison(source_cursor,target_cursor,tenant,
             "public",target_schema,t,src[t],dst[t])
             for t in sorted(set(src)&set(dst))]
    critical=[r for r in results if r["kind"]=="BUSINESS" and r["status"]!="MATCH"]
    transient=[r for r in results if r["kind"]=="TRANSIENT" and r["status"]!="MATCH"]
    project_roles = FINANCE_ROLES if target_schema in (
        "csb_finance","gpp_piutang","gpp_finance_cabang"
    ) else KLARIN_ROLES
    if tenant_role not in project_roles:
        raise NoGo("Tenant role does not belong to destination BASE")
    others=[role for role in project_roles if role!=tenant_role]
    target_cursor.execute("""
      SELECT count(*)::int,
      count(*) FILTER(WHERE c.relrowsecurity)::int,
      bool_and(has_table_privilege(%s,c.oid,'SELECT')) AS tenant_read,
      bool_and(NOT has_table_privilege('anon',c.oid,'SELECT')) AS anon_denied,
      bool_and(NOT has_table_privilege('authenticated',c.oid,'SELECT')) AS browser_denied,
      bool_and(NOT EXISTS (
         SELECT 1 FROM unnest(%s::text[]) AS other(role)
         WHERE has_table_privilege(other.role,c.oid,'SELECT')
      )) AS cross_tenant_denied
      FROM pg_class c JOIN pg_namespace n ON c.relnamespace=n.oid
      WHERE n.nspname=%s AND c.relkind='r' AND NOT c.relispartition
    """,(tenant_role,others,target_schema))
    table_count,rls_count,read_ok,anon_ok,browser_ok,cross_denied=target_cursor.fetchone()
    return {
        "tenant":tenant, "common_tables":len(results),
        "business_matching":sum(r["kind"]=="BUSINESS" and r["status"]=="MATCH" for r in results),
        "business_drift":critical, "transient_drift":transient,
        "missing_target_tables":missing_tables,
        "extra_target_tables":sorted(set(dst)-set(src)),
        "target_rls_tables":int(rls_count),
        "target_total_tables":int(table_count),
        "acl_pass":bool(read_ok and anon_ok and browser_ok and cross_denied
                         and table_count==rls_count and table_count>0),
    }

def claim_bucket_inventory(cursor,bucket: str) -> dict:
    if bucket not in ("klarin-private-attachments","gpro-csb-private-attachments","gpp-klarin-attachments","gpro-gpp-private-attachments"):
        raise NoGo("Unexpected private Storage bucket")
    cursor.execute("""
       SELECT b.public,count(o.id)::bigint,
         coalesce(sum(CASE WHEN o.metadata->>'size' ~ '^[0-9]+$'
           THEN (o.metadata->>'size')::bigint ELSE 0 END),0)::bigint
       FROM storage.buckets b
       LEFT JOIN storage.objects o ON o.bucket_id=b.id
       WHERE b.id=%s GROUP BY b.public
    """,(bucket,))
    row=cursor.fetchone()
    if row is None: raise NoGo("Expected private Storage bucket missing")
    return {"private":row[0] is False, "objects":int(row[1]),"metadata_bytes":int(row[2])}

def dedicated_role_credentials(cursor, roles: tuple[str,...]) -> dict:
    if not roles or any(not IDENT.fullmatch(r) for r in roles):
        raise NoGo("Invalid dedicated roles list")
    cursor.execute("""
       SELECT count(*)::int,
              count(*) FILTER(WHERE rolcanlogin)::int,
              count(*) FILTER(WHERE rolpassword IS NOT NULL)::int
       FROM pg_authid WHERE rolname=ANY(%s)
    """,(list(roles),))
    n,can_login,has_password=cursor.fetchone()
    return {"roles":int(n),"login_roles":int(can_login),"configured_credentials":int(has_password),
            "required":len(roles),"pass":n==len(roles) and can_login==n and has_password==n}

def assemble_report(tenants: list[dict], finance_roles: dict, klarin_roles: dict,
                    source_files: dict,target_files: dict,
                    gpp_stock_source_files: dict,gpp_stock_target_files: dict) -> dict:
    business_drift=sum(len(t["business_drift"])+len(t["missing_target_tables"]) for t in tenants)
    acl_pass=all(t["acl_pass"] for t in tenants)
    db_data_pass=business_drift==0
    bucket_metadata_parity=bool(
       source_files["private"] and target_files["private"]
       and source_files["objects"]==target_files["objects"]
       and source_files["metadata_bytes"]==target_files["metadata_bytes"]
       and source_files["objects"]>0
    )
    gpp_bucket_metadata_parity=bool(
       gpp_stock_source_files["private"] and gpp_stock_target_files["private"]
       and gpp_stock_source_files["objects"]==gpp_stock_target_files["objects"]
       and gpp_stock_source_files["metadata_bytes"]==gpp_stock_target_files["metadata_bytes"]
       and gpp_stock_source_files["objects"]>0
    )
    return {
       "mode":"SEVEN_TO_TWO_READ_ONLY_LIVE_CENSUS",
       "source_projects":5,"target_projects":2,
       "tenants":tenants,
       "total_common_tables":sum(t["common_tables"] for t in tenants),
       "business_table_drift_count":business_drift,
       "business_data_parity_pass":db_data_pass,
       "all_tenant_rls_acl_pass":acl_pass,
       "finance_dedicated_pg_roles":finance_roles,
       "klarin_dedicated_pg_roles":klarin_roles,
       "csb_private_source_storage":source_files,
       "csb_private_target_storage":target_files,
       "csb_storage_metadata_parity_pass":bucket_metadata_parity,
       # GPP Stock original private objects require independent target-byte proof.
       "gpp_stock_legacy_source_storage":gpp_stock_source_files,
       "gpp_stock_target_storage":gpp_stock_target_files,
       "gpp_stock_storage_metadata_parity_pass":gpp_bucket_metadata_parity,
       "gpp_stock_original_target_bytes_verified":False,
       "requires_external_independently_verified_proof":[
          "actual complete seven-project PostgreSQL restore",
          "physical Storage original/target byte SHA256 and restore drill for CSB Klarin and GPP Stock",
          "signed business write freeze and final frozen snapshot",
          "five distinct least-privilege authenticated tenant login/writer E2E",
          "green unchanged application release quality gates and tested rollback",
          "responsible owner data-residency and cutover approval",
       ],
       "cutover_ready":False,
       "delete_or_pause_legacy_projects":False,
    }

def live_report() -> dict:
    try:
        import psycopg
    except ImportError:
        raise NoGo("psycopg3 is required in the protected operator environment") from None
    conns={}
    try:
        for name,(ref,env_name) in PROJECTS.items():
            dsn=os.environ.get(env_name,"")
            pinned_owner_dsn(dsn,ref)
            mode=parse_qs(urlsplit(dsn).query).get("sslmode",["require"])[0]
            c=psycopg.connect(dsn,sslmode=mode,connect_timeout=12,autocommit=True)
            conns[name]=c
            with c.cursor() as cur:
                cur.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                cur.execute("SET LOCAL statement_timeout='120000ms'")
                cur.execute("SELECT current_user")
                if cur.fetchone()[0]!="postgres":
                    raise NoGo("Only approved operator owner can perform protected census")
        tenants=[]
        for tenant,source,target,schema,role in TENANTS:
            with conns[source].cursor() as sc,conns[target].cursor() as tc:
                tenants.append(inspect_tenant(sc,tc,tenant,schema,role))
        with conns["finance_base"].cursor() as c:
            fr=dedicated_role_credentials(c,FINANCE_ROLES)
        with conns["klarin_base"].cursor() as c:
            kr=dedicated_role_credentials(c,KLARIN_ROLES)
        with conns["csb_klarin_old"].cursor() as c:
            source_files=claim_bucket_inventory(c,"klarin-private-attachments")
        with conns["klarin_base"].cursor() as c:
            target_files=claim_bucket_inventory(c,"gpro-csb-private-attachments")
        with conns["gpp_stock_old"].cursor() as c:
            gpp_stock_source_files=claim_bucket_inventory(c,"gpp-klarin-attachments")
        with conns["klarin_base"].cursor() as c:
            gpp_stock_target_files=claim_bucket_inventory(c,"gpro-gpp-private-attachments")
        return assemble_report(tenants,fr,kr,source_files,target_files,
                               gpp_stock_source_files,gpp_stock_target_files)
    except Exception:
        # psycopg exceptions can contain connection strings or private details.
        raise NoGo("Protected read-only reconciliation failed; inspect privately") from None
    finally:
        for conn in conns.values():
            try:
                with conn.cursor() as cur:
                    cur.execute("ROLLBACK")
                conn.close()
            except Exception:
                try:conn.close()
                except Exception:pass

def main() -> int:
    parser=argparse.ArgumentParser(description="Fail-closed seven-project SQL census (no writes or deletion)")
    parser.add_argument("--live",action="store_true",help="Use exact operator-held DSNs for seven read-only snapshots")
    args=parser.parse_args()
    if not args.live:
        print(json.dumps({
            "mode":"OFFLINE_NO_NETWORK","projects_expected":7,
            "required_env_names":sorted(key for _,key in PROJECTS.values()),
            "network_calls":0,"writes":0,"cutover_ready":False,
        },sort_keys=True))
        return 0
    try:
        print(json.dumps(live_report(),sort_keys=True))
        return 0
    except (NoGo,ValueError):
        print("NO-GO: protected seven-project read-only census did not complete",
              file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
