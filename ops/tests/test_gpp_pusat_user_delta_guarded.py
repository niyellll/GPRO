"""Pure offline GPP Pusat account safety tests. All values synthetic."""
import argparse
import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"gpp_pusat_user_delta_guarded.py"
spec=importlib.util.spec_from_file_location("gpp_pusat_user_delta_guarded",SCRIPT)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def row(n,**kw):
    d=dict(id="synthetic-id-"+str(n),username="synthetic-user-"+str(n),
           password="synthetic-hash-"+str(n),role="operator",created_at="2026-11-18",
           version=2,active=None,expiry=None,updated_at="2026-11-19")
    d.update(kw)
    return (d["id"],d["username"],d["password"],d["role"],d["created_at"],
            d["version"],d["active"],d["expiry"],d["updated_at"])

def arguments(**changes):
    d=dict(apply=False,approved_change_ref="",verified_restore_ref="",
           confirm_frozen_writes=False,confirm_session_reauthentication=False,
           expected_missing_role="",expected_source_rows=None,expected_target_rows=None,
           expected_source_sha256="",expected_target_sha256="")
    d.update(changes)
    return argparse.Namespace(**d)

class MissingGppUserTests(unittest.TestCase):
    def test_exact_projects_and_schema_are_pinned(self):
        self.assertEqual(mod.SOURCE_REF,"vmpurwykfzcmculnnjfw")
        self.assertEqual(mod.TARGET_REF,"fdhqidjltlihzdcbqfrd")
        self.assertEqual(mod.SOURCE_TABLE,"public.users")
        self.assertEqual(mod.TARGET_TABLE,"gpp_piutang.users")
        self.assertEqual(len(mod.COLUMNS),9)

    def test_dry_run_is_not_blocked_by_missing_operator_signoff(self):
        mod.approval_gate(arguments())

    def test_apply_requires_full_restore_freeze_and_session_reset_approval(self):
        correct=dict(apply=True,approved_change_ref="signed",
                     verified_restore_ref="isolated-physical-storage-and-postgres-restore",
                     confirm_frozen_writes=True,confirm_session_reauthentication=True,
                     expected_missing_role="operator",
                     expected_source_rows=6,expected_target_rows=5,
                     expected_source_sha256="a"*64,expected_target_sha256="b"*64)
        mod.approval_gate(arguments(**correct))
        for key,bad in (
            ("approved_change_ref",""),("verified_restore_ref",""),
            ("confirm_frozen_writes",False),("confirm_session_reauthentication",False),
            ("expected_missing_role",""),("expected_source_rows",5),
            ("expected_target_rows",6),("expected_source_sha256","bad"),
            ("expected_target_sha256",""),("apply",True),
        ):
            opts=correct.copy()
            if key=="apply":opts.pop("approved_change_ref")
            else:opts[key]=bad
            with self.subTest(key=key),self.assertRaises(mod.UserTransferBlocked):
                mod.approval_gate(arguments(**opts))

    def test_admin_or_owner_role_needs_independent_review(self):
        opts=arguments(apply=True,approved_change_ref="signed",
             verified_restore_ref="real-restore",confirm_frozen_writes=True,
             confirm_session_reauthentication=True,expected_source_rows=6,
             expected_target_rows=5,expected_source_sha256="a"*64,
             expected_target_sha256="b"*64,expected_missing_role="superadmin")
        with self.assertRaises(mod.UserTransferBlocked):
            mod.approval_gate(opts)

    def test_exact_direct_owner_connection_only(self):
        good=f"postgresql://postgres:synthetic@db.{mod.SOURCE_REF}.supabase.co:5432/postgres?sslmode=require"
        mod.assert_owner_dsn(good,mod.SOURCE_REF)
        for url in (
            good.replace("postgres:","gpro_gpp_pusat:",1),
            good.replace(mod.SOURCE_REF,mod.TARGET_REF),
            good.replace(":5432/",":5433/"),
            good.replace("/postgres?","/other?"),
            good.replace("sslmode=require","sslmode=disable"),
        ):
            with self.subTest(url=url.split("@")[-1]),self.assertRaises(mod.UserTransferBlocked):
                mod.assert_owner_dsn(url,mod.SOURCE_REF)

    def test_pooler_owner_username_bound_to_exact_project(self):
        good=f"postgresql://postgres.{mod.TARGET_REF}:synthetic@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
        mod.assert_owner_dsn(good,mod.TARGET_REF)
        for url in (
            good.replace("postgres."+mod.TARGET_REF,"postgres."+mod.SOURCE_REF),
            good.replace("postgres."+mod.TARGET_REF,"gpro_gpp_pusat."+mod.TARGET_REF),
            good.replace("pooler.supabase.com","pooler.supabase.com.evil.invalid"),
        ):
            with self.subTest(url=url.split("@")[-1]),self.assertRaises(mod.UserTransferBlocked):
                mod.assert_owner_dsn(url,mod.TARGET_REF)

    def test_stable_fingerprint_omits_volatile_session_fields(self):
        src=mod.stable_fingerprint_sql(mod.SOURCE_TABLE)
        tgt=mod.stable_fingerprint_sql(mod.TARGET_TABLE)
        for sql in (src,tgt):
            self.assertIn("jsonb_build_object",sql)
            self.assertIn("password",sql)
            self.assertIn("ORDER BY id",sql)
            self.assertNotIn("active_session_id",sql)
            self.assertNotIn("auth_session_version",sql)
            self.assertNotIn("updated_at",sql)
        with self.assertRaises(mod.UserTransferBlocked):
            mod.stable_fingerprint_sql("public.some_other_tenant")

    def test_exact_one_missing_account_allowed(self):
        src=[row(i) for i in range(6)]
        dst=src[:5]
        self.assertEqual(mod.find_missing(src,dst),src[5])

    def test_existing_target_session_drift_is_not_a_credential_conflict(self):
        src=[row(i) for i in range(6)]
        dst=[row(i,version=8,updated_at="another timestamp") for i in range(5)]
        self.assertEqual(mod.find_missing(src,dst),src[5])

    def test_existing_password_change_is_never_overwritten(self):
        src=[row(i) for i in range(6)]
        dst=src[:4]+[row(4,password="different-hash")]
        with self.assertRaises(mod.UserTransferBlocked):
            mod.find_missing(src,dst)

    def test_target_only_user_causes_no_go(self):
        src=[row(i) for i in range(6)]
        dst=src[:5]+[row(99)]
        with self.assertRaises(mod.UserTransferBlocked):
            mod.find_missing(src,dst)

    def test_two_missing_accounts_or_no_missing_account_causes_no_go(self):
        src=[row(i) for i in range(6)]
        for dst in (src[:4],src):
            with self.assertRaises(mod.UserTransferBlocked):
                mod.find_missing(src,dst)

    def test_missing_account_with_session_cannot_be_transferred(self):
        src=[row(i) for i in range(5)]
        for missing in (row(5,active="live-token"),
                        row(5,expiry="2026-12-01")):
            with self.subTest(missing=bool(missing[6])),self.assertRaises(mod.UserTransferBlocked):
                mod.find_missing(src+[missing],src)

    def test_username_collision_blocks_even_with_distinct_uuids(self):
        src=[row(i) for i in range(5)]+[row(5,username="synthetic-user-1")]
        with self.assertRaises(mod.UserTransferBlocked):
            mod.find_missing(src,src[:5])

    def test_empty_missing_credential_role_and_version_overflow_blocked(self):
        base=[row(i) for i in range(5)]
        variants=(row(5,password=""),row(5,role=""),
                  row(5,version=-1),row(5,version=9223372036854775807))
        for item in variants:
            with self.subTest(case=item[5]),self.assertRaises(mod.UserTransferBlocked):
                mod.find_missing(base+[item],base)

    def test_sql_checks_real_tenant_security_and_never_changes_existing_users(self):
        s=SCRIPT.read_text(encoding="utf-8")
        self.assertIn('tc.execute("LOCK TABLE gpp_piutang.users IN SHARE ROW EXCLUSIVE MODE")',s)
        self.assertIn("target_ready(tc)",s)
        self.assertIn("row not in after for row in target_rows",s)
        self.assertIn("missing[5]+1",s)
        self.assertIn("None,None",s.replace(" ",""))
        self.assertNotIn("ON CONFLICT DO UPDATE",s)
        self.assertNotIn("DELETE FROM",s)
        self.assertNotIn("TRUNCATE",s)
        self.assertIn('tc.execute("COMMIT")',s)

    def test_secrets_and_user_identity_are_not_logged(self):
        s=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("GPRO_GPP_PUSAT_USER_SOURCE_DSN",s)
        self.assertIn("GPRO_GPP_PUSAT_USER_TARGET_DSN",s)
        self.assertNotIn("print(missing",s)
        self.assertNotIn("print(source_rows",s)
        self.assertNotIn("print(source_dsn",s)
        self.assertNotIn("postgresql://postgres:",s)

if __name__=="__main__":
    unittest.main()
