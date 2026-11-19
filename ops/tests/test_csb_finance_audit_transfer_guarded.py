"""CSB Finance audit append-only: pure synthetic safety tests; no SQL/credentials."""
import argparse
import importlib.util
from pathlib import Path
import unittest

FILE=Path(__file__).resolve().parents[1]/"scripts"/"csb_finance_audit_transfer_guarded.py"
spec=importlib.util.spec_from_file_location("csb_finance_audit_transfer_guarded",FILE)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def opts(**overrides):
    defaults=dict(apply=False,confirm_frozen_writes=False,approved_change_ref="",
                  verified_restore_ref="",expected_source_rows=None,
                  expected_target_rows=None,expected_source_sha256="")
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class AuditDeltaGuardTests(unittest.TestCase):
    def test_projects_and_schema_are_fixed_and_separate(self):
        self.assertEqual(mod.SOURCE_REF,"lmbvbgkqvidtkzxtvtpe")
        self.assertEqual(mod.TARGET_REF,"fdhqidjltlihzdcbqfrd")
        self.assertNotEqual(mod.SOURCE_REF,mod.TARGET_REF)
        self.assertEqual(mod.SOURCE_TABLE,"public.audit_logs")
        self.assertEqual(mod.TARGET_TABLE,"csb_finance.audit_logs")
        self.assertEqual(len(mod.COLUMNS),11)

    def test_dry_run_requires_no_apply_authorization(self):
        mod.approval_gate(opts())

    def test_apply_without_backup_proof_is_rejected(self):
        with self.assertRaises(mod.AuditTransferBlocked):
            mod.approval_gate(opts(apply=True,expected_source_rows=298,expected_target_rows=293,
                                   expected_source_sha256="a"*64))

    def test_apply_requires_source_and_target_counts_and_exact_hash(self):
        valid=opts(apply=True,confirm_frozen_writes=True,approved_change_ref="approved",
                   verified_restore_ref="restore-test-ok",expected_source_rows=298,
                   expected_target_rows=293,expected_source_sha256="a"*64)
        mod.approval_gate(valid)
        valid.expected_target_rows=None
        with self.assertRaises(mod.AuditTransferBlocked):
            mod.approval_gate(valid)

    def test_invalid_source_hash_is_rejected(self):
        with self.assertRaises(mod.AuditTransferBlocked):
            mod.approval_gate(opts(apply=True,confirm_frozen_writes=True,
                approved_change_ref="approved",verified_restore_ref="verified",
                expected_source_rows=298,expected_target_rows=293,
                expected_source_sha256="not-a-hash"))

    def test_direct_and_pooler_endpoints_are_pinned(self):
        good=f"postgresql://postgres:synthetic@db.{mod.SOURCE_REF}.supabase.co:5432/postgres"
        mod.assert_pinned_dsn(good,mod.SOURCE_REF)
        with self.assertRaises(mod.AuditTransferBlocked):
            mod.assert_pinned_dsn(good,mod.TARGET_REF)
        pool=f"postgresql://postgres.{mod.TARGET_REF}:synthetic@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
        mod.assert_pinned_dsn(pool,mod.TARGET_REF)

    def test_http_wrong_host_or_insecure_tls_rejected(self):
        for raw in ("https://example.com", "postgresql://postgres:fixture@db.wrong.supabase.co/postgres",
                    f"postgresql://postgres:fixture@db.{mod.TARGET_REF}.supabase.co/postgres?sslmode=disable"):
            with self.assertRaises(mod.AuditTransferBlocked):
                mod.assert_pinned_dsn(raw,mod.TARGET_REF)

    def test_append_only_delta_is_deterministic_and_idempotent(self):
        src=[("one","record"),("two","record"),("three","record")]
        dst=[("one","record")]
        self.assertEqual(mod.delta(src,dst),src[1:])
        self.assertEqual(mod.delta(src,src),[])

    def test_target_only_uuid_rejected(self):
        with self.assertRaises(mod.AuditTransferBlocked):
            mod.delta([("one","r")],[("one","r"),("extra","r")])

    def test_same_uuid_changed_json_rejected(self):
        with self.assertRaises(mod.AuditTransferBlocked):
            mod.delta([("one",{"audit":1})],[("one",{"audit":2})])

    def test_duplicate_uuid_rejected(self):
        with self.assertRaises(mod.AuditTransferBlocked):
            mod.delta([("one","x"),("one","x")],[])

    def test_canonical_sql_fingerprint_ordered_and_only_allowlisted(self):
        for table in (mod.SOURCE_TABLE,mod.TARGET_TABLE):
            sql=mod.fingerprint_sql(table)
            self.assertIn("ORDER BY id",sql)
            self.assertIn("to_jsonb(t)::text",sql)
            self.assertIn("sha256(",sql)
        with self.assertRaises(mod.AuditTransferBlocked):
            mod.fingerprint_sql("public.users")

    def test_all_server_privileges_must_be_separately_checked(self):
        text=FILE.read_text(encoding="utf-8")
        for privilege in ("SELECT","INSERT","UPDATE","DELETE"):
            self.assertIn("has_table_privilege('service_role',%s,'"+privilege+"')",text)
        self.assertNotIn("'SELECT,INSERT,UPDATE,DELETE'",text)
        self.assertIn("target_ready(tc)",text)

    def test_no_credentials_in_repo_and_apply_has_no_overwrites(self):
        text=FILE.read_text(encoding="utf-8")
        self.assertIn("GPRO_CSB_AUDIT_SOURCE_DSN",text)
        self.assertIn("GPRO_CSB_AUDIT_TARGET_DSN",text)
        self.assertIn("READ ONLY",text)
        self.assertIn("SERIALIZABLE",text)
        self.assertNotIn("ON CONFLICT DO UPDATE",text)
        self.assertNotIn("DELETE FROM",text)
        self.assertNotIn("TRUNCATE",text)
        self.assertIn('tc.execute("COMMIT")',text)


if __name__=="__main__":
    unittest.main()
