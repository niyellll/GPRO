"""No-network synthetic tests. Never include real Storage tokens or customer files."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"csb_klarin_storage_stage_guarded.py"
sys.path.insert(0,str(SCRIPT.parent))
spec=importlib.util.spec_from_file_location("csb_klarin_storage_stage_guarded",SCRIPT)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
FAKE_BLOB=b"%PDF-1.7 SYNTHETIC TEST FIXTURE, NOT A REAL CUSTOMER FILE"
FAKE_KEY1="synthetic_source_service_key_not_valid_for_any_project_123"
FAKE_KEY2="synthetic_target_service_key_not_valid_for_any_project_456"


class FakeStorageTransport:
    def __init__(self, entry, source_blob=FAKE_BLOB, target_blob=None):
        self.objects={}
        self.calls=[]
        source_url=mod.storage_url(mod.SOURCE_REF,mod.SOURCE_BUCKET,
                                   entry["storage_path"],private_read=True)
        target_url=mod.storage_url(mod.TARGET_REF,mod.TARGET_BUCKET,
                                   entry["storage_path"],private_read=True)
        self.objects[source_url]=source_blob
        if target_blob is not None:
            self.objects[target_url]=target_blob

    def request(self,method,url,key,*,data=None,content_type=None,maximum_bytes=0):
        self.calls.append((method,url,content_type))
        if method=="GET":
            value=self.objects.get(url)
            if value is not None and len(value)>maximum_bytes:
                raise mod.StageBlocked("Object exceeds limit")
            return value
        if method!="POST":
            raise mod.StageBlocked("Unexpected method")
        assert key==FAKE_KEY2
        assert content_type=="application/pdf"
        assert "object/authenticated" not in url
        assert "/gpro-csb-private-attachments/" in url
        assert url.startswith("https://"+mod.TARGET_REF+".supabase.co/")
        path=url.replace("/storage/v1/object/","/storage/v1/object/authenticated/",1)
        if path in self.objects:
            raise mod.StageBlocked("Forbidden upsert")
        self.objects[path]=data
        return b""


def approved(**patch):
    data=dict(
        apply=True, approved_change_ref="operator-signed-change",
        verified_restore_ref="actual-isolated-restore-drill-proof",
        frozen_inventory_ref="verified-frozen-inventory",
        confirm_frozen_writes=True,
        source_state_sha256="a"*64,target_state_sha256="b"*64,
        source_root="/secure/original",target_root="/secure/readback"
    )
    data.update(patch)
    return argparse.Namespace(**data)


class StorageStageTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base=Path(self.tmp.name)
        self.source=base/"source"
        self.target=base/"target"
        self.source.mkdir(mode=0o700)
        self.target.mkdir(mode=0o700)
        self.entry={
            "id":"synthetic1","owner_type":"klaim","owner_id":"owner1",
            "file_name":"sample.pdf","mime_type":"application/pdf",
            "size_bytes":len(FAKE_BLOB),
            "storage_path":"attachments/owner1/sample.pdf",
            "expected_sha256":hashlib.sha256(FAKE_BLOB).hexdigest()
        }
        self.manifest=base/"private.json"
        self.manifest.write_text(json.dumps([self.entry]),encoding="utf-8")

    def load(self):
        from csb_klarin_storage_byte_audit import private_manifest
        return private_manifest(self.manifest)

    def transfer(self,transport=None):
        return mod.stage_objects(self.load(),len(FAKE_BLOB),
            self.source,self.target,FAKE_KEY1,FAKE_KEY2,
            transport or FakeStorageTransport(self.entry))

    def test_pinned_source_and_target_bucket_names_are_distinct(self):
        src=mod.storage_url(mod.SOURCE_REF,mod.SOURCE_BUCKET,
                            self.entry["storage_path"],private_read=True)
        dst=mod.storage_url(mod.TARGET_REF,mod.TARGET_BUCKET,
                            self.entry["storage_path"],private_read=False)
        self.assertTrue(src.startswith("https://"+mod.SOURCE_REF+".supabase.co/"))
        self.assertIn("/object/authenticated/klarin-private-attachments/",src)
        self.assertIn("/object/gpro-csb-private-attachments/",dst)
        self.assertNotEqual(src,dst)
        with self.assertRaises(mod.StageBlocked):
            mod.storage_url(mod.SOURCE_REF,mod.TARGET_BUCKET,"file.pdf",private_read=False)
        with self.assertRaises(mod.StageBlocked):
            mod.storage_url(mod.TARGET_REF,mod.SOURCE_BUCKET,"file.pdf",private_read=True)

    def test_reject_path_traversal_even_when_project_is_correct(self):
        for path in ("../secret.pdf","a/../../evil.pdf","/root/key","a//b"):
            with self.subTest(path=path),self.assertRaises(ValueError):
                mod.storage_url(mod.TARGET_REF,mod.TARGET_BUCKET,path,private_read=False)

    def test_offline_dry_run_requires_no_approvals_or_keys(self):
        mod.approval_gate(approved(apply=False,approved_change_ref="",
                                   confirmed=False, source_state_sha256=""))
        self.assertEqual(mod.manifest_gate(self.load(),1,len(FAKE_BLOB)),1)

    def test_apply_requires_backup_restore_freeze_and_state_hashes(self):
        mod.approval_gate(approved())
        for change in (
            {"approved_change_ref":""},{"verified_restore_ref":""},
            {"frozen_inventory_ref":""},{"confirm_frozen_writes":False},
            {"source_state_sha256":""},{"target_state_sha256":"not-a-sha"},
            {"target_root":""},
        ):
            with self.subTest(change=change),self.assertRaises(mod.StageBlocked):
                mod.approval_gate(approved(**change))

    def test_manifest_requires_independent_hash_and_full_inventory(self):
        with self.assertRaises(mod.StageBlocked):
            mod.manifest_gate(self.load(),6,2918989)
        with self.assertRaises(mod.StageBlocked):
            mod.manifest_gate(self.load(),1,len(FAKE_BLOB)+1)
        bad=dict(self.entry)
        bad.pop("expected_sha256")
        self.manifest.write_text(json.dumps([bad]),encoding="utf-8")
        with self.assertRaises(mod.StageBlocked):
            mod.manifest_gate(self.load(),1,len(FAKE_BLOB))

    def test_separate_server_only_keys_and_not_in_repo(self):
        env={mod.SOURCE_SECRET:FAKE_KEY1,mod.TARGET_SECRET:FAKE_KEY2}
        self.assertEqual(mod.service_tokens(env),(FAKE_KEY1,FAKE_KEY2))
        env[mod.TARGET_SECRET]=FAKE_KEY1
        with self.assertRaises(mod.StageBlocked):
            mod.service_tokens(env)
        env[mod.TARGET_SECRET]="short"
        with self.assertRaises(mod.StageBlocked):
            mod.service_tokens(env)
        with self.assertRaises(mod.StageBlocked):
            mod.service_tokens({})

    def test_stages_once_and_verifies_real_synthetic_byte_readback(self):
        transport=FakeStorageTransport(self.entry)
        summary=self.transfer(transport)
        self.assertEqual(summary["objects"],1)
        self.assertEqual(summary["bytes"],len(FAKE_BLOB))
        self.assertEqual(summary["objects_uploaded"],1)
        self.assertEqual(summary["objects_reused_after_sha256"],0)
        self.assertTrue(summary["verified_source_and_target_sha256"])
        self.assertFalse(summary["ready_for_cutover"])
        self.assertEqual((self.source/self.entry["storage_path"]).read_bytes(),FAKE_BLOB)
        self.assertEqual((self.target/self.entry["storage_path"]).read_bytes(),FAKE_BLOB)
        self.assertEqual([c[0] for c in transport.calls],["GET","GET","POST","GET"])
        self.assertNotIn("sample.pdf",str(summary))
        self.assertNotIn("owner1",str(summary))
        self.assertNotIn(FAKE_KEY1,str(summary))

    def test_exact_existing_target_object_is_reused_not_overwritten(self):
        transport=FakeStorageTransport(self.entry,target_blob=FAKE_BLOB)
        summary=self.transfer(transport)
        self.assertEqual(summary["objects_uploaded"],0)
        self.assertEqual(summary["objects_reused_after_sha256"],1)
        self.assertEqual([c[0] for c in transport.calls],["GET","GET"])
        self.assertFalse(summary["ready_for_cutover"])

    def test_mismatched_existing_target_bytes_are_never_overwritten(self):
        blob=b"!" + FAKE_BLOB[1:]
        transport=FakeStorageTransport(self.entry,target_blob=blob)
        with self.assertRaises(mod.StageBlocked):
            self.transfer(transport)
        self.assertFalse(any(method=="POST" for method,_,_ in transport.calls))

    def test_source_sha256_mismatch_blocks_before_upload(self):
        blob=b"!" + FAKE_BLOB[1:]
        transport=FakeStorageTransport(self.entry,source_blob=blob)
        with self.assertRaises(mod.StageBlocked):
            self.transfer(transport)
        self.assertEqual([c[0] for c in transport.calls],["GET"])

    def test_missing_source_fails_closed_without_target_write(self):
        transport=FakeStorageTransport(self.entry,source_blob=None)
        with self.assertRaises(mod.StageBlocked):
            self.transfer(transport)
        self.assertFalse(any(c[0]=="POST" for c in transport.calls))

    def test_post_upload_readback_missing_is_rejected(self):
        class BrokenReadback(FakeStorageTransport):
            def request(self,*a,**kw):
                data=super().request(*a,**kw)
                if a[0]=="GET" and a[1].startswith("https://"+mod.TARGET_REF):
                    return None
                return data
        with self.assertRaises(mod.StageBlocked):
            self.transfer(BrokenReadback(self.entry))

    def test_tampered_local_copy_cannot_be_replaced(self):
        existing=self.source/self.entry["storage_path"]
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b"!" + FAKE_BLOB[1:])
        with self.assertRaises((mod.StageBlocked,ValueError)):
            self.transfer()

    def test_unknown_or_world_readable_local_roots_are_rejected(self):
        with self.assertRaises((mod.StageBlocked,ValueError)):
            mod.stage_objects(self.load(),len(FAKE_BLOB),
                self.source,self.source,FAKE_KEY1,FAKE_KEY2,
                FakeStorageTransport(self.entry))
        if sys.platform!="win32":
            self.source.chmod(0o755)
            with self.assertRaises((mod.StageBlocked,ValueError)):
                self.transfer()

    def test_source_and_target_contents_never_enter_git_or_output(self):
        text=SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"ready_for_cutover": False',text)
        self.assertIn('"x-upsert"] = "false"',text)
        self.assertIn('GPRO_CSB_KLARIN_SOURCE_STORAGE_SERVICE_KEY',text)
        self.assertIn('GPRO_CSB_KLARIN_TARGET_STORAGE_SERVICE_KEY',text)
        self.assertNotIn("DELETE FROM",text)
        self.assertNotIn("storage.objects INSERT",text)
        self.assertNotIn("print(entry",text)
        self.assertNotIn("print(data",text)


if __name__=="__main__":
    unittest.main()
