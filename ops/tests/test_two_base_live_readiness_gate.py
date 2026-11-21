"""Entirely synthetic/offline tests: no Supabase network, credentials, customer data."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"two_base_live_readiness_gate.py"
spec=importlib.util.spec_from_file_location("two_base_live_readiness_gate",SCRIPT)
assert spec and spec.loader
gate=importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)

class FakeCursor:
    def __init__(self,rows):
        self.rows=rows
        self.last_query=""
        self.last_params=None
    def execute(self,query,params=None):
        self.last_query=query
        self.last_params=params
    def fetchone(self):
        return self.rows[0] if self.rows else None
    def fetchall(self):
        return self.rows

def tenant_result(tenant,drift=None,acl=True):
    return {"tenant":tenant,"common_tables":20,
            "business_matching":19 if drift else 20,
            "business_drift":drift or [],
            "transient_drift":[],
            "missing_target_tables":[],
            "extra_target_tables":[],
            "target_rls_tables":20,"target_total_tables":20,
            "acl_pass":acl}

def roles(n):
    return {"roles":n,"login_roles":n,"configured_credentials":n,
            "required":n,"pass":True}

def files(objects=6,bytes_count=2918989):
    return {"private":True,"objects":objects,"metadata_bytes":bytes_count}

class TwoBaseLiveReadinessTests(unittest.TestCase):
    def test_exactly_two_base_and_five_legacy_project_pins(self):
        self.assertEqual(len(gate.PROJECTS),7)
        self.assertEqual(len({x[0] for x in gate.PROJECTS.values()}),7)
        self.assertEqual(gate.PROJECTS["finance_base"][0],"fdhqidjltlihzdcbqfrd")
        self.assertEqual(gate.PROJECTS["klarin_base"][0],"numlkqppirrxfwdhazja")
        self.assertEqual(len(gate.TENANTS),5)
        self.assertEqual(set(t[3] for t in gate.TENANTS),
             {"csb_finance","gpp_piutang","gpp_finance_cabang","csb_klarin","gpp_stock"})

    def test_source_to_target_tenant_identity_never_crossed(self):
        for label,source,target,schema,role in gate.TENANTS:
            self.assertNotEqual(source,target)
            self.assertIn(source,gate.PROJECTS)
            self.assertIn(target,("finance_base","klarin_base"))
            self.assertIn(schema,{"csb_finance","gpp_piutang",
                "gpp_finance_cabang","csb_klarin","gpp_stock"})
            self.assertTrue(role.startswith("gpro_"))

    def test_direct_owner_postgres_exact_project_tls_required(self):
        ref=gate.PROJECTS["finance_base"][0]
        dsn=f"postgresql://postgres:synthetic-only@db.{ref}.supabase.co:5432/postgres?sslmode=require"
        self.assertTrue(gate.pinned_owner_dsn(dsn,ref))
        self.assertTrue(gate.pinned_owner_dsn(dsn.replace("require","verify-full"),ref))
        for bad in (
            dsn.replace("postgres:","gpro_gpp_pusat:",1),
            dsn.replace(ref,gate.PROJECTS["klarin_base"][0]),
            dsn.replace("5432/","5433/"),
            dsn.replace("/postgres?","/bad_database?"),
            dsn.replace("sslmode=require","sslmode=disable"),
            dsn.replace("sslmode=require","sslmode=require&host=evil.invalid"),
        ):
            with self.subTest(case=bad.split("@")[-1]),self.assertRaises(gate.NoGo):
                gate.pinned_owner_dsn(bad,ref)

    def test_pooler_owner_identity_is_bound_to_project_ref(self):
        ref=gate.PROJECTS["klarin_base"][0]
        dsn=f"postgresql://postgres.{ref}:synthetic@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
        self.assertTrue(gate.pinned_owner_dsn(dsn,ref))
        self.assertTrue(gate.pinned_owner_dsn(dsn.replace(":5432/",":6543/"),ref))
        for bad in (
            dsn.replace("postgres."+ref,"postgres"),
            dsn.replace("postgres."+ref,"postgres."+gate.PROJECTS["finance_base"][0]),
            dsn.replace("pooler.supabase.com","pooler.supabase.com.evil.invalid"),
            dsn.replace(":5432/",":443/"),
        ):
            with self.subTest(case=bad.split("@")[-1]),self.assertRaises(gate.NoGo):
                gate.pinned_owner_dsn(bad,ref)

    def test_unexpected_or_sql_injection_identifiers_are_rejected(self):
        self.assertEqual(gate.sql_ident("csb_finance"),'"csb_finance"')
        for item in ("public;DROP SCHEMA","x-y","a.b","",'"public"',None,"00bad"):
            with self.subTest(item=item),self.assertRaises(gate.NoGo):
                gate.sql_ident(item)

    def test_per_row_multiset_sha_is_order_independent_and_read_only(self):
        sql=gate.normalized_row_sql("gpp_piutang","users",set())
        self.assertIn("FROM \"gpp_piutang\".\"users\" t",sql)
        self.assertIn("ORDER BY rowhash",sql)
        self.assertIn("sha256(convert_to",sql)
        self.assertNotIn("DELETE",sql)
        self.assertNotIn("UPDATE",sql)
        self.assertNotIn("TRUNCATE",sql)
        self.assertNotIn("INSERT",sql)

    def test_normalized_target_compatibility_columns_excluded_without_data_loss(self):
        source={"id","value","created_at"}
        target=source|{"compatibility_match","migrated_source"}
        sr,dr,kind=gate.classify_table("gpp_pusat","rekening_koran_working_lines_v439",source,target)
        self.assertEqual(sr,set())
        self.assertEqual(dr,{"compatibility_match","migrated_source"})
        self.assertEqual(kind,"BUSINESS")
        sql=gate.normalized_row_sql("gpp_piutang","rekening_koran_working_lines_v439",dr)
        self.assertIn("compatibility_match",sql)
        self.assertIn("migrated_source",sql)
        self.assertNotIn("COALESCE(is_active",sql)

    def test_missing_source_column_in_target_is_hard_blocker(self):
        sr,dr,kind=gate.classify_table("csb_finance","audit_logs",
                                       {"id","new_data","old_data"},{"id","new_data"})
        self.assertEqual(kind,"SCHEMA_MISMATCH")

    def test_user_table_preserves_credentials_roles_but_ignores_volatile_sessions(self):
        cols={"id","username","password","role","created_at",
              "auth_session_version","updated_at","active_session_id"}
        a,b,kind=gate.classify_table("gpp_pusat","users",cols,cols)
        self.assertEqual(a,{"auth_session_version","updated_at","active_session_id"})
        self.assertEqual(a,b)
        self.assertEqual(kind,"BUSINESS")
        q=gate.normalized_row_sql("public","users",a)
        self.assertIn("'auth_session_version'",q)
        self.assertIn("'active_session_id'",q)
        self.assertIn("to_jsonb(t)",q)

    def test_session_and_rate_limit_tables_classified_volatile_not_business(self):
        for table in ("login_rate_limits","klarin_sessions"):
            self.assertEqual(gate.classify_table("csb_finance",table,
                {"id"},{"id"})[2],"TRANSIENT")
        self.assertEqual(gate.classify_table("csb_klarin",
                     "klarin_stock_claim_app_state",{"id"},{"id"})[2],"BUSINESS")

    def test_private_bucket_inventory_rejects_bbms_other_bucket(self):
        with self.assertRaises(gate.NoGo):
            gate.claim_bucket_inventory(FakeCursor([(False,0,0)]),"bbm-private-files")

    def test_private_bucket_inventory_checks_only_metadata_not_file_bytes(self):
        cursor=FakeCursor([(False,6,2918989)])
        self.assertEqual(gate.claim_bucket_inventory(cursor,
           "gpro-csb-private-attachments"),files())
        self.assertIn("storage.objects",cursor.last_query)
        self.assertIn("storage.buckets",cursor.last_query)
        self.assertEqual(cursor.last_params,("gpro-csb-private-attachments",))

    def test_gpp_stock_private_source_inventory_included_without_fake_transfer(self):
        cursor=FakeCursor([(False,2,4231865)])
        self.assertEqual(gate.claim_bucket_inventory(cursor,
            "gpp-klarin-attachments"),files(2,4231865))
        people=[tenant_result(x) for x in ("csb_finance","gpp_pusat",
            "gpp_cabang","csb_klarin","gpp_stock")]
        report=gate.assemble_report(people,roles(3),roles(2),
            files(),files(),files(2,4231865))
        self.assertEqual(report["gpp_stock_legacy_source_storage"]["objects"],2)
        self.assertEqual(report["gpp_stock_legacy_source_storage"]["metadata_bytes"],4231865)
        self.assertFalse(report["gpp_stock_original_target_bytes_verified"])
        self.assertFalse(report["cutover_ready"])

    def test_dedicated_login_role_gate_checks_real_password_presence(self):
        c=FakeCursor([(3,3,0)])
        value=gate.dedicated_role_credentials(c,gate.FINANCE_ROLES)
        self.assertEqual(value["configured_credentials"],0)
        self.assertFalse(value["pass"])
        self.assertIn("pg_authid",c.last_query)
        self.assertNotIn("rolpassword::text",c.last_query)

    def test_no_go_on_business_drift_even_if_other_tenants_match(self):
        people=[tenant_result("gpp_pusat",
                 [{"table":"users","kind":"BUSINESS","status":"DRIFT",
                   "source_count":6,"target_count":5}])]
        people+= [tenant_result(x) for x in ("csb_finance","gpp_cabang","csb_klarin","gpp_stock")]
        result=gate.assemble_report(people,roles(3),roles(2),files(),files(),files(2,4231865))
        self.assertEqual(result["business_table_drift_count"],1)
        self.assertFalse(result["business_data_parity_pass"])
        self.assertFalse(result["cutover_ready"])

    def test_no_go_if_private_file_object_count_misses_six(self):
        people=[tenant_result(x) for x in ("csb_finance","gpp_pusat",
                     "gpp_cabang","csb_klarin","gpp_stock")]
        report=gate.assemble_report(people,roles(3),roles(2),files(),files(0,0),files(2,4231865))
        self.assertFalse(report["csb_storage_metadata_parity_pass"])
        self.assertFalse(report["cutover_ready"])

    def test_all_green_metadata_still_never_authorizes_project_deletion(self):
        people=[tenant_result(x) for x in ("csb_finance","gpp_pusat",
                     "gpp_cabang","csb_klarin","gpp_stock")]
        report=gate.assemble_report(people,roles(3),roles(2),files(),files(),files(2,4231865))
        self.assertTrue(report["business_data_parity_pass"])
        self.assertTrue(report["csb_storage_metadata_parity_pass"])
        self.assertFalse(report["cutover_ready"])
        self.assertFalse(report["delete_or_pause_legacy_projects"])
        self.assertGreater(len(report["requires_external_independently_verified_proof"]),4)

    def test_no_mutation_or_deletion_hidden_in_live_census(self):
        code=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",code)
        self.assertIn('cur.execute("ROLLBACK")',code)
        self.assertIn('"cutover_ready":False',code)
        self.assertNotIn("DROP PROJECT",code)
        self.assertNotIn("DELETE FROM",code)
        self.assertNotIn("INSERT INTO",code)
        self.assertNotIn("ALTER ROLE",code)
        self.assertNotIn("DROP SCHEMA",code)

if __name__=="__main__":
    unittest.main()
