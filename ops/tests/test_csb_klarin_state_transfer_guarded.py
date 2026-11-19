"""CSB Klarin guarded PostgreSQL/Storage transfer: synthetic offline tests only.

No network, no DB credential and NO live claim/attachment data.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "csb_klarin_state_transfer_guarded.py"
sys.path.insert(0,str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("csb_klarin_state_transfer_guarded",SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
SOURCE_REF=mod.SOURCE_REF
TARGET_REF=mod.TARGET_REF
TEST_PASSWORD="FAKE-TEST-ONLY"
FAKE_DATA=b"synthetic CSB claim attachment, no real customer bytes"


def options(**patch):
    defaults={
        "apply":False,"source_version":None,"target_version":None,
        "source_sha256":"","target_sha256":"","expected_attachments":None,
        "expected_total_bytes":None,"approved_change_ref":"",
        "verified_restore_ref":"","confirm_frozen_writes":False,
        "manifest":"","source_root":"","target_root":"",
    }
    defaults.update(patch)
    return argparse.Namespace(**defaults)


class GuardedCsbKlarinTransferTests(unittest.TestCase):
    def test_correct_pinned_source_and_target_projects(self):
        self.assertNotEqual(SOURCE_REF,TARGET_REF)
        self.assertEqual(mod.SOURCE_BUCKET,"klarin-private-attachments")
        self.assertEqual(mod.TARGET_BUCKET,"gpro-csb-private-attachments")
        self.assertEqual(mod.TARGET_SCHEMA,"csb_klarin")
        self.assertEqual(len(mod.ATTACH_COLUMNS),11)

    def test_strict_direct_supabase_operator_connection(self):
        for ref in (SOURCE_REF,TARGET_REF):
            url=f"postgresql://postgres:{TEST_PASSWORD}@db.{ref}.supabase.co:5432/postgres?sslmode=require"
            mod.require_operator_url(url,ref)
            with self.assertRaises(mod.TransferBlocked):
                mod.require_operator_url(url,TARGET_REF if ref==SOURCE_REF else SOURCE_REF)

    def test_strict_pooled_supabase_operator_connection(self):
        u=f"postgresql://postgres.{TARGET_REF}:{TEST_PASSWORD}@aws-0-ap-south-1.pooler.supabase.com:5432/postgres"
        mod.require_operator_url(u,TARGET_REF)
        with self.assertRaises(mod.TransferBlocked):
            mod.require_operator_url(u,SOURCE_REF)

    def test_reject_user_role_admin_or_unsafe_url_override(self):
        samples=(
            f"postgresql://gpro_csb_klarin:{TEST_PASSWORD}@db.{TARGET_REF}.supabase.co:5432/postgres",
            f"postgresql://postgres:{TEST_PASSWORD}@db.{TARGET_REF}.supabase.co:5432/other",
            f"postgresql://postgres:{TEST_PASSWORD}@evil.example.invalid:5432/postgres",
            f"postgresql://postgres.{TARGET_REF}:{TEST_PASSWORD}@notpooler.example.invalid:6543/postgres",
            f"postgresql://postgres:{TEST_PASSWORD}@db.{TARGET_REF}.supabase.co:5432/postgres?sslmode=disable",
            f"postgresql://postgres:{TEST_PASSWORD}@db.{TARGET_REF}.supabase.co:5432/postgres?host=other",
            f"postgresql://postgres@db.{TARGET_REF}.supabase.co:5432/postgres",
            f"https://postgres:{TEST_PASSWORD}@db.{TARGET_REF}.supabase.co/postgres",
        )
        for raw in samples:
            with self.subTest(case=raw.split("@")[-1]):
                with self.assertRaises(mod.TransferBlocked):
                    mod.require_operator_url(raw,TARGET_REF)

    def test_default_dry_run_does_not_require_cutover_authorization(self):
        mod.require_approval(options())

    def test_apply_requires_restore_freeze_hashes_and_private_copies(self):
        with self.assertRaises(mod.TransferBlocked):
            mod.require_approval(options(apply=True))
        approved=options(
            apply=True,source_version=40,target_version=38,
            source_sha256="a"*64,target_sha256="b"*64,
            expected_attachments=6,expected_total_bytes=2918989,
            approved_change_ref="signed-change",verified_restore_ref="isolated-restore",
            confirm_frozen_writes=True,manifest="/private/manifest.json",
            source_root="/private/source",target_root="/private/target",
        )
        mod.require_approval(approved)
        approved.expected_attachments=0
        with self.assertRaises(mod.TransferBlocked):
            mod.require_approval(approved)

    def test_exact_source_and_target_file_inventory(self):
        sample=[
            {"storage_path":"file/one.pdf","size_bytes":35,"data_base64":""},
            {"storage_path":"file/two.xlsx","size_bytes":99,"data_base64":""},
        ]
        obj={"file/one.pdf":35,"file/two.xlsx":99}
        self.assertEqual(mod.assert_original_objects(sample,obj,obj),obj)
        with self.assertRaises(mod.TransferBlocked):
            mod.assert_original_objects(sample,obj,{"file/one.pdf":35})

    def test_extra_target_object_or_inline_attachment_blocks(self):
        m=[{"storage_path":"one","size_bytes":5,"data_base64":""}]
        with self.assertRaises(mod.TransferBlocked):
            mod.assert_original_objects(m,{"one":5},{"one":5,"other":1})
        m[0]["data_base64"]="not-empty"
        with self.assertRaises(mod.TransferBlocked):
            mod.assert_original_objects(m,{"one":5},{"one":5})

    def test_attachment_metadata_exact_except_server_migrated_timestamp(self):
        original={k:"v" for k in mod.ATTACH_COLUMNS}
        identical=original.copy()
        identical["storage_migrated_at"]="different"
        self.assertTrue(mod.attachment_record_equal(original,identical))
        identical["uploaded_by"]="tampered"
        self.assertFalse(mod.attachment_record_equal(original,identical))

    def test_merge_preserves_existing_and_rebuilds_source_in_order(self):
        src={"version":40,"state":{
          "monitoringKlaim":[{"id":"claim1","status":"ok"}],
          "uploadBatches":[{"id":"batch1","name":"first"},{"id":"batch2","name":"new"}],
          "auditLogs":[{"id":"log1","action":"prior"},{"id":"log2","action":"add"}],
          "other":{"safe":True},
        }}
        dst={"version":38,"state":{
          "monitoringKlaim":[],
          "uploadBatches":[{"id":"batch1","name":"first"}],
          "auditLogs":[{"id":"log1","action":"prior"}],
          "other":{"safe":True},
        }}
        result=mod.merged_state(src,dst)
        self.assertEqual(result,src["state"])

    def test_merge_rejects_existing_business_id_conflicts(self):
        src={"version":40,"state":{
          "monitoringKlaim":[{"id":"claim1"}],
          "uploadBatches":[{"id":"batch1","name":"first"}],
          "auditLogs":[{"id":"log1"}],"other":True,
        }}
        dst={"version":38,"state":{
          "monitoringKlaim":[],
          "uploadBatches":[{"id":"batch1","name":"wrong"}],
          "auditLogs":[{"id":"log1"}],"other":True,
        }}
        with self.assertRaises(mod.TransferBlocked):
            mod.merged_state(src,dst)

    def test_real_byte_parity_verification_uses_temporary_synthetic_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            sroot=root/"source";troot=root/"target"
            for folder in (sroot,troot):
                file=folder/"claims"/"sample.pdf"
                file.parent.mkdir(parents=True)
                file.write_bytes(FAKE_DATA)
            entry={
                "id":"file1","owner_type":"klaim","owner_id":"claim1",
                "file_name":"sample.pdf","mime_type":"application/pdf",
                "size_bytes":len(FAKE_DATA),"storage_path":"claims/sample.pdf",
                "expected_sha256":hashlib.sha256(FAKE_DATA).hexdigest(),
            }
            manifest=root/"private.json"
            manifest.write_text(json.dumps([entry]),encoding="utf-8")
            args=options(manifest=str(manifest),source_root=str(sroot),
                         target_root=str(troot),expected_attachments=1,
                         expected_total_bytes=len(FAKE_DATA))
            mod.verify_private_byte_proof(args,[entry])
            (troot/"claims"/"sample.pdf").write_bytes(b"x"+FAKE_DATA[1:])
            with self.assertRaises(mod.TransferBlocked):
                mod.verify_private_byte_proof(args,[entry])

    def test_missing_independent_sha256_proof_blocks_apply(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            entry={
                "id":"file1","owner_type":"klaim","owner_id":"claim1",
                "file_name":"sample.pdf","mime_type":"application/pdf",
                "size_bytes":len(FAKE_DATA),"storage_path":"claims/sample.pdf",
            }
            manifest=root/"private.json";manifest.write_text(json.dumps([entry]))
            args=options(manifest=str(manifest),source_root=str(root),
                         target_root=str(root),expected_attachments=1,
                         expected_total_bytes=len(FAKE_DATA))
            with self.assertRaises(mod.TransferBlocked):
                mod.verify_private_byte_proof(args,[entry])

    def test_sql_mutations_require_serializable_cas_and_never_drop(self):
        code=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("ISOLATION LEVEL SERIALIZABLE",code)
        self.assertIn("FOR UPDATE",code)
        self.assertIn("AND version=%s AND state=%s::jsonb",code)
        self.assertIn("source_target_bytes_equal",code)
        self.assertIn('tc.execute("COMMIT")',code)
        self.assertNotIn("TRUNCATE",code)
        self.assertNotIn("DROP TABLE",code)
        self.assertNotIn("DELETE FROM",code)
        self.assertNotIn("ON CONFLICT DO UPDATE",code)

    def test_no_browser_secret_or_broad_shared_writer(self):
        code=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("GPRO_CSB_KLARIN_SOURCE_DSN",code)
        self.assertIn("GPRO_CSB_KLARIN_TARGET_DSN",code)
        self.assertIn("has_table_privilege('service_role',%s,%s)",code)
        self.assertIn('if tc.fetchone()["role"]!="postgres"',code)
        self.assertNotIn("NEXT_PUBLIC_",code)
        self.assertNotIn("set role service_role",code.lower())


if __name__=="__main__":
    unittest.main()
