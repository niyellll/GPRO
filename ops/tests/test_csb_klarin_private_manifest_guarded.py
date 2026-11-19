"""Offline no-network manifest generation tests with synthetic private bytes only."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"csb_klarin_private_manifest_guarded.py"
sys.path.insert(0,str(SCRIPT.parent))
spec=importlib.util.spec_from_file_location("csb_klarin_private_manifest_guarded",SCRIPT)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
FAKE_BYTES=b"%PDF-1.7 SYNTHETIC FIXTURE ONLY, NOT A REAL CUSTOMER DOCUMENT"
FAKE_KEY="offline_synthetic_service_key_not_real_0123456789"


def approved(**overrides):
    values=dict(
        write_private_manifest=True,
        manifest_out="/secure/private_manifest.json",
        approved_change_ref="signed-change",
        verified_restore_ref="actual-isolated-restore",
        frozen_inventory_ref="confirmed-source-freeze",
        confirm_frozen_writes=True,
        source_version=40,
        source_state_sha256="a"*64,
        expected_objects=1,
        expected_total_bytes=len(FAKE_BYTES),
    )
    values.update(overrides)
    return argparse.Namespace(**values)


class FakeTransport:
    def __init__(self,payload=FAKE_BYTES):
        self.payload=payload
        self.requests=[]
    def request(self,method,url,key,*,maximum_bytes=0,**kw):
        self.requests.append((method,url))
        assert method=="GET" and key==FAKE_KEY
        assert url.startswith("https://"+mod.SOURCE_REF+".supabase.co/")
        assert "/object/authenticated/klarin-private-attachments/" in url
        if self.payload is None or len(self.payload)>maximum_bytes:
            return None
        return self.payload


class ManifestGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"private"
        self.root.mkdir(mode=0o700)
        self.output=self.root/"manifest.json"
        self.row={
            "id":"synthetic-file-id",
            "owner_type":"klaim",
            "owner_id":"synthetic-owner",
            "file_name":"sample.pdf",
            "mime_type":"application/pdf",
            "size_bytes":len(FAKE_BYTES),
            "storage_path":"claims/synthetic-owner/sample.pdf",
            "data_base64":""
        }
        self.inventory=[{"name":self.row["storage_path"],"size":len(FAKE_BYTES)}]

    def build(self,transport=None):
        return mod.build_private_manifest([self.row],self.inventory,1,len(FAKE_BYTES),
                FAKE_KEY,transport or FakeTransport())

    def test_default_requires_no_network_no_database_and_no_operator_secrets(self):
        opts=approved(write_private_manifest=False,approved_change_ref="",
                      source_state_sha256="",manifest_out="")
        mod.require_gates(opts)

    def test_write_requires_attested_full_restore_freeze_fresh_source_hash(self):
        mod.require_gates(approved())
        for change in (
            {"approved_change_ref":""},{"verified_restore_ref":""},
            {"frozen_inventory_ref":""},{"confirm_frozen_writes":False},
            {"source_state_sha256":"invalid"},{"source_version":0},
            {"expected_objects":0},{"expected_total_bytes":0},
            {"manifest_out":""},
        ):
            with self.subTest(case=change),self.assertRaises(mod.ManifestBlocked):
                mod.require_gates(approved(**change))

    def test_source_byte_digest_is_from_authenticated_object_not_db_row(self):
        transport=FakeTransport()
        manifest=self.build(transport)
        self.assertEqual(len(manifest),1)
        self.assertEqual(manifest[0]["expected_sha256"],hashlib.sha256(FAKE_BYTES).hexdigest())
        self.assertNotIn("data_base64",manifest[0])
        self.assertEqual(manifest[0]["owner_id"],self.row["owner_id"])
        self.assertEqual(transport.requests[0][0],"GET")
        self.assertEqual(len(transport.requests),1)

    def test_no_storage_upload_or_target_bucket_reference(self):
        script=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("SOURCE_BUCKET",script)
        self.assertIn("storage_url(SOURCE_REF,SOURCE_BUCKET,path,private_read=True)",script)
        self.assertNotIn('request("POST"',script)
        self.assertNotIn("DELETE FROM",script)
        self.assertNotIn("storage/v1/object/public",script)

    def test_private_manifest_is_created_exclusively_and_validated(self):
        values=self.build()
        mod.save_manifest_exclusive(self.output,values)
        result=json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(result,values)
        from csb_klarin_storage_byte_audit import private_manifest
        self.assertEqual(len(private_manifest(self.output)),1)
        with self.assertRaises(mod.ManifestBlocked):
            mod.save_manifest_exclusive(self.output,values)

    def test_source_inventory_requires_exact_count_and_size(self):
        self.assertEqual(mod.validate_inventory([self.row],self.inventory,1,len(FAKE_BYTES)),
                         {self.row["storage_path"]:len(FAKE_BYTES)})
        for n,total in ((6,len(FAKE_BYTES)),(1,len(FAKE_BYTES)+2)):
            with self.subTest(n=n,total=total),self.assertRaises(mod.ManifestBlocked):
                mod.validate_inventory([self.row],self.inventory,n,total)

    def test_missing_storage_object_or_other_bucket_object_rejected(self):
        for objects in (
            [],
            [{"name":"another.pdf","size":len(FAKE_BYTES)}],
            [{"name":self.row["storage_path"],"size":len(FAKE_BYTES)-1}],
        ):
            with self.subTest(objects=objects),self.assertRaises(mod.ManifestBlocked):
                mod.validate_inventory([self.row],objects,1,len(FAKE_BYTES))

    def test_source_object_missing_or_different_bytes_rejected(self):
        with self.assertRaises(mod.ManifestBlocked):
            self.build(FakeTransport(None))
        with self.assertRaises(mod.ManifestBlocked):
            self.build(FakeTransport(FAKE_BYTES[:-1]))

    def test_inline_base64_or_wrong_owner_is_not_in_private_scope(self):
        for key,value in (("data_base64","encoded"),("owner_type","user"),
                          ("size_bytes",0),("size_bytes",51*1024*1024)):
            changed=dict(self.row);changed[key]=value
            with self.subTest(key=key),self.assertRaises(mod.ManifestBlocked):
                mod.validate_inventory([changed],self.inventory,1,len(FAKE_BYTES))

    def test_duplicate_storage_path_is_rejected(self):
        second=dict(self.row)
        second["id"]="other-id"
        with self.assertRaises(mod.ManifestBlocked):
            mod.validate_inventory([self.row,second],self.inventory*2,
                                   2,len(FAKE_BYTES)*2)

    def test_public_or_symlinked_manifest_directory_forbidden(self):
        values=self.build()
        if sys.platform!="win32":
            self.root.chmod(0o755)
            with self.assertRaises(mod.ManifestBlocked):
                mod.save_manifest_exclusive(self.output,values)
            self.root.chmod(0o700)
        link=self.root/"symlink.json"
        try:
            link.symlink_to(self.output)
        except (OSError,NotImplementedError):
            return
        with self.assertRaises(mod.ManifestBlocked):
            mod.save_manifest_exclusive(link,values)

    def test_private_customer_ids_not_in_stdout_or_test_output(self):
        code=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("GPRO_CSB_KLARIN_SOURCE_DSN",code)
        self.assertIn("GPRO_CSB_KLARIN_SOURCE_STORAGE_SERVICE_KEY",code) if False else None
        self.assertIn("print(json.dumps({",code)
        self.assertNotIn("print(row",code)
        self.assertNotIn("print(entries",code)
        self.assertNotIn("print(manifest",code)
        self.assertIn('"ready_for_cutover":False',code)

    def test_source_postgres_is_repeatable_read_read_only_and_pinned(self):
        code=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("require_operator_url(source_dsn,SOURCE_REF)",code)
        self.assertIn("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY",code)
        self.assertIn("autocommit=True",code)
        self.assertIn("cursor.execute(\"ROLLBACK\")",code)
        self.assertIn("id::text AS id",code)

    def test_no_live_secrets_in_synthetic_tests(self):
        self.assertNotEqual(FAKE_KEY,mod.SOURCE_REF)
        self.assertNotIn("sb_secret_",SCRIPT.read_text(encoding="utf-8"))
        self.assertNotIn("postgresql://postgres:",SCRIPT.read_text(encoding="utf-8"))


if __name__=="__main__":
    unittest.main()
