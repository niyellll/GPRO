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
            for extra in mod.NEW_COLUMNS:
                self.assertIn(f"- '{extra}'", query)
        with self.assertRaises(ValueError):
            mod.fingerprint_query("csb_finance")

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
