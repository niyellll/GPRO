"""Static contracts: the live two-BASE role gates are READ ONLY and non-secret.

Do not expose DB role password values or silently give tenant roles DML.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1] / "sql"
FINANCE = ROOT / "two_base_finance_tenant_role_gate_READ_ONLY.sql"
KLARIN = ROOT / "two_base_klarin_tenant_role_gate_READ_ONLY.sql"


class TwoBaseTenantRoleGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.finance = FINANCE.read_text(encoding="utf-8")
        cls.klarin = KLARIN.read_text(encoding="utf-8")

    def test_exact_tenant_roles_and_schemas(self):
        for role,schema in (
            ("gpro_csb_finance","csb_finance"),
            ("gpro_gpp_pusat","gpp_piutang"),
            ("gpro_gpp_cabang","gpp_finance_cabang"),
        ):
            self.assertIn(f"('{role}','{schema}')",self.finance)
        for role,schema in (
            ("gpro_csb_klarin","csb_klarin"),
            ("gpro_gpp_stock","gpp_stock"),
        ):
            self.assertIn(f"('{role}','{schema}')",self.klarin)

    def test_cross_schema_access_and_write_rights_are_reported(self):
        for text in (self.finance,self.klarin):
            for field in (
                "expected_schema_usage",
                "expected_tables_with_rls",
                "expected_tables_selectable",
                "expected_tables_insertable",
                "expected_tables_updateable",
                "expected_tables_deletable",
                "cross_schema_selectable",
                "cross_schema_insertable",
                "other_schema_usage_count",
            ):
                self.assertIn(field,text)

    def test_no_database_credential_or_hash_disclosed(self):
        for text in (self.finance,self.klarin):
            self.assertIn("(a.rolpassword IS NOT NULL) AS credential_configured",text)
            self.assertNotRegex(text,r"(?i)\bSELECT\s+\*\s+FROM\s+pg_authid\b")
            self.assertNotIn("a.rolpassword AS",text)
            self.assertNotIn("PASSWORD '",text)

    def test_read_only_sql_no_privilege_or_data_change(self):
        for text in (self.finance,self.klarin):
            active=re.sub(r"--[^\n]*","",text)
            for bad in (r"\bGRANT\s",r"\bREVOKE\s",r"\bDROP\s",
                        r"\bDELETE\s+FROM\b",r"\bINSERT\s+INTO\b",
                        r"\bUPDATE\s+\S+\s+SET\b",r"\bALTER\s+TABLE\b"):
                self.assertNotRegex(active,re.compile(bad,re.I))

    def test_role_gates_cannot_mistake_read_only_for_live_login(self):
        for text in (self.finance,self.klarin):
            self.assertIn("This cannot prove actual network LOGIN",text)
            self.assertIn("r.rolcanlogin AS login_flag",text)
            self.assertIn("credential_configured",text)

if __name__=="__main__":
    unittest.main()
