"""No-network, no-secrets contract tests for guarded GPP RK transfer utility."""
import argparse
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "gpp_rk_transfer_guarded.py"
spec = importlib.util.spec_from_file_location("gpp_rk_transfer_guarded", SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class GuardedTransferTests(unittest.TestCase):
    def test_source_and_target_are_different_pinned_projects(self):
        self.assertNotEqual(mod.SOURCE_REF, mod.TARGET_REF)
        self.assertEqual(len(mod.COLUMNS), 22)
        self.assertEqual(len(mod.NEW_COLUMNS), 3)
        self.assertEqual(len(set(mod.COLUMNS)), 22)

    def test_dry_run_requires_no_change_approval(self):
        options = argparse.Namespace(apply=False, confirm_frozen_writes=False,
            approved_change_ref="", verified_restore_ref="", expected_rows=None,
            expected_sha256="")
        mod.check_approval(options)

    def test_apply_fails_closed_without_restore_freeze_and_checksum(self):
        options = argparse.Namespace(apply=True, confirm_frozen_writes=False,
            approved_change_ref="", verified_restore_ref="", expected_rows=None,
            expected_sha256="")
        with self.assertRaises(ValueError):
            mod.check_approval(options)

    def test_apply_requires_complete_explicit_authority_gate(self):
        options = argparse.Namespace(apply=True, confirm_frozen_writes=True,
            approved_change_ref="reviewed-operator-change", verified_restore_ref="restored-snapshot",
            expected_rows=47, expected_sha256="a" * 64)
        mod.check_approval(options)
        options.expected_sha256 = "invalid"
        with self.assertRaises(ValueError):
            mod.check_approval(options)

    def test_reject_wrong_project_for_direct_supabase_url(self):
        bad = "postgresql://postgres:fixture-only@db.wrongproject.supabase.co:5432/postgres"
        with self.assertRaises(ValueError):
            mod.require_correct_project(bad, mod.SOURCE_REF)

    def test_allow_only_pinned_source_direct_host(self):
        good = f"postgresql://postgres:fixture-only@db.{mod.SOURCE_REF}.supabase.co:5432/postgres"
        mod.require_correct_project(good, mod.SOURCE_REF)
        with self.assertRaises(ValueError):
            mod.require_correct_project(good, mod.TARGET_REF)

    def test_allow_only_pooler_role_of_target_project(self):
        good = (f"postgresql://postgres.{mod.TARGET_REF}:fixture-only"
                "@aws-0-ap-south-1.pooler.supabase.com:5432/postgres")
        mod.require_correct_project(good, mod.TARGET_REF)
        with self.assertRaises(ValueError):
            mod.require_correct_project(good, mod.SOURCE_REF)

    def test_fingerprint_is_sha256_and_schema_allowlisted(self):
        for name in ("public", "gpp_piutang"):
            query = mod.fingerprint_query(name)
            self.assertIn("sha256(", query)
            self.assertIn(f"FROM {name}.rekening_koran_working_lines_v439", query)
            self.assertIn("jsonb_build_object(", query)
            for column in mod.COLUMNS:
                self.assertIn("'" + column + "', t." + column, query)
            for extra in mod.NEW_COLUMNS:
                self.assertNotIn("'" + extra + "', t." + extra, query)
        with self.assertRaises(ValueError):
            mod.fingerprint_query("csb_finance")

    def test_service_crud_privileges_and_period_rls_are_independently_required(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("period_rls", text)
        self.assertIn("period_own", text)
        self.assertIn('for privilege in ("SELECT","INSERT","UPDATE","DELETE"):',text)
        self.assertIn("has_table_privilege('service_role',%s,%s)",text)
        self.assertNotIn("'SELECT,INSERT,UPDATE,DELETE'",text)

    def test_repeated_business_signatures_block_even_with_distinct_uuid(self):
        class FakeCursor:
            def execute(self, sql):
                self.sql = sql
            def fetchone(self):
                return (47, 94)
        cursor = FakeCursor()
        with self.assertRaisesRegex(ValueError, "NO-GO"):
            mod.require_no_duplicate_business_signatures(cursor)
        self.assertIn("GROUP BY bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo",cursor.sql)
        self.assertIn("HAVING count(*)>1",cursor.sql)
        self.assertNotIn("select *",cursor.sql.lower())

    def test_zero_business_signature_duplicates_pass(self):
        class FakeCursor:
            def execute(self, sql):
                pass
            def fetchone(self):
                return (0,0)
        mod.require_no_duplicate_business_signatures(FakeCursor())

    def test_source_business_signature_check_precedes_row_fingerprint(self):
        script=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("require_no_duplicate_business_signatures(sc)",script)
        self.assertLess(script.index("require_no_duplicate_business_signatures(sc)"),
                        script.index('sc.execute(fingerprint_query("public"))'))
        self.assertNotIn("DELETE FROM public.rekening_koran_working_lines_v439",script)

    def test_static_source_does_not_hardcode_database_password(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("GPRO_RK_SOURCE_DSN", text)
        self.assertIn("GPRO_RK_TARGET_DSN", text)
        self.assertIn("if not args.apply:", text)
        self.assertIn("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY", text)
        self.assertIn("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE", text)
        self.assertIn('tc.execute("COMMIT")', text)
        self.assertIn('tc.execute("ROLLBACK")', text)
        self.assertNotIn("password='", text)


if __name__ == "__main__":
    unittest.main()
