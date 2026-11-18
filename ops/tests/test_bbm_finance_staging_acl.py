"""Offline review contracts for legacy BBM Finance V635 staging exposure.

No DB access, no migration-key material, no permission changes in CI.
"""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT / "sql" / "bbm_finance_v635_staging_anon_acl_READ_ONLY.sql"
REVIEW=ROOT / "sql" / "bbm_finance_v635_stage_revoke_anon_REVIEW_ONLY.sql"
EXPECTED=(
    "bbm_v635_stage_accounts",
    "bbm_v635_stage_audit_logs",
    "bbm_v635_stage_bbm_accounting_controls_v333",
    "bbm_v635_stage_customers",
    "bbm_v635_stage_excel_data",
    "bbm_v635_stage_journal_details",
    "bbm_v635_stage_journals",
    "bbm_v635_stage_rekening_koran",
    "bbm_v635_stage_users",
)


class AnonStageReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=REPORT.read_text(encoding="utf-8")
        cls.review=REVIEW.read_text(encoding="utf-8")

    def test_nine_exact_whitelisted_tables_only(self):
        for t in EXPECTED:
            self.assertIn(t,self.report)
            self.assertIn(t,self.review)
        self.assertEqual(len(set(EXPECTED)),9)
        self.assertNotIn("gpp_piutang.",self.review)
        self.assertNotIn("csb_finance.",self.review)
        self.assertNotIn("gpp_finance_cabang.",self.review)

    def test_report_must_be_read_only(self):
        sql=re.sub(r"--[^\n]*","",self.report)
        self.assertIn("has_table_privilege('anon'",sql)
        self.assertIn("pg_policies",sql)
        self.assertNotRegex(sql,r"(?i)\b(?:REVOKE|GRANT|UPDATE|INSERT\s+INTO|DELETE\s+FROM|DROP|ALTER)\b")

    def test_remediation_is_explicitly_not_applied(self):
        self.assertIn("REVIEW ONLY, NOT APPLIED",self.review)
        self.assertIn("DO $preflight$",self.review)
        self.assertIn("DO $verify$",self.review)
        self.assertIn("BEGIN;",self.review)
        self.assertIn("COMMIT;",self.review)
        self.assertIn("REVOKE INSERT ON TABLE",self.review)
        self.assertIn("FROM anon",self.review)

    def test_no_drop_delete_grant_or_schema_mutation(self):
        sql=re.sub(r"--[^\n]*","",self.review)
        self.assertNotRegex(sql,r"(?i)\b(?:DROP|TRUNCATE|DELETE\s+FROM|INSERT\s+INTO|UPDATE\s+\S+\s+SET|GRANT|ALTER\s+TABLE)\b")
        self.assertIn("FROM anon;",sql)

    def test_abort_on_data_unexpected_grants_or_rls(self):
        for marker in (
            "rows_found <> 0",
            "c.relrowsecurity",
            "has_table_privilege('anon', relation_oid, 'INSERT')",
            "has_table_privilege('service_role', relation_oid, 'SELECT,INSERT,UPDATE,DELETE')",
            "staging table contains records",
            "post-revoke privileges invalid",
        ):
            self.assertIn(marker,self.review)

    def test_never_publish_staging_shared_key(self):
        for source in (self.report,self.review):
            # Staging security proof is in RLS metadata; never copy its fixed key into Git.
            self.assertNotRegex(source,r"v635stage_[0-9a-fA-F]{16,}")
            self.assertIn("migration",source)

    def test_preflight_is_locked_against_concurrent_writers(self):
        sql=self.review
        self.assertIn("LOCK TABLE",sql)
        self.assertIn("IN SHARE ROW EXCLUSIVE MODE;",sql)
        lock_at=sql.index("LOCK TABLE")
        preflight_at=sql.index("DO $preflight$")
        revoke_at=sql.index("REVOKE INSERT ON TABLE")
        self.assertLess(lock_at,preflight_at)
        self.assertLess(preflight_at,revoke_at)
        lock_sql=sql[lock_at:preflight_at]
        for table in EXPECTED:
            self.assertIn("public."+table,lock_sql)

    def test_only_one_scope_of_anon_revocation(self):
        body=re.sub(r"--[^\n]*","",self.review)
        self.assertEqual(len(re.findall(r"\bREVOKE\s+INSERT\s+ON\s+TABLE\b",body,flags=re.I)),1)
        self.assertEqual(len(re.findall(r"\bCOMMIT\s*;",body,flags=re.I)),1)

if __name__=="__main__":
    unittest.main()
