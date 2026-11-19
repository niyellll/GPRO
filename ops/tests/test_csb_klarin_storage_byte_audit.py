"""No-network, synthetic temporary files only. Never checks live customer files."""
import copy
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "csb_klarin_storage_byte_audit.py"
spec = importlib.util.spec_from_file_location("csb_klarin_storage_byte_audit", SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DATA = b"synthetic file fixture - not a real claim"


class StorageByteAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = pathlib.Path(self.temp.name)
        self.source = base / "source"
        self.target = base / "target"
        self.source.mkdir()
        self.target.mkdir()
        self.entry = {
            "id": "file_1", "owner_type": "klaim", "owner_id": "claim_1",
            "file_name": "synthetic.pdf", "mime_type": "application/pdf",
            "size_bytes": len(DATA), "storage_path": "claims/claim_1/synthetic.pdf",
            "expected_sha256": hashlib.sha256(DATA).hexdigest(),
        }
        for root in (self.source,self.target):
            p = root / self.entry["storage_path"]
            p.parent.mkdir(parents=True)
            p.write_bytes(DATA)
        self.manifest = base / "private_manifest.json"
        self.manifest.write_text(json.dumps([self.entry]),encoding="utf-8")

    def load(self):
        return mod.private_manifest(self.manifest)

    def test_matching_source_and_target_proves_bytes_but_not_cutover(self):
        output = mod.audit(self.load(), self.source, self.target)
        self.assertEqual(output["objects"],1)
        self.assertEqual(output["bytes_checked"],len(DATA))
        self.assertTrue(output["source_target_bytes_equal"])
        self.assertFalse(output["ready_for_cutover"])
        self.assertNotIn("claim_1",str(output))
        self.assertNotIn("synthetic.pdf",str(output))

    def test_source_only_does_not_claim_target_parity(self):
        output = mod.audit(self.load(), self.source)
        self.assertTrue(output["source_file_lengths_verified"])
        self.assertEqual(output["source_sha256_digests_computed"],1)
        self.assertEqual(output["source_expected_sha256_proofs_verified"],1)
        self.assertFalse(output["source_target_bytes_equal"])
        self.assertFalse(output["ready_for_cutover"])

    def test_mutated_target_file_same_length_fails(self):
        p = self.target / self.entry["storage_path"]
        p.write_bytes(b"X" + DATA[1:])
        with self.assertRaises(mod.ByteAuditBlocked):
            mod.audit(self.load(),self.source,self.target)

    def test_wrong_source_manifest_sha_fails(self):
        self.entry["expected_sha256"] = "a" * 64
        self.manifest.write_text(json.dumps([self.entry]),encoding="utf-8")
        with self.assertRaises(mod.ByteAuditBlocked):
            mod.audit(self.load(),self.source,self.target)

    def test_truncated_file_is_blocked(self):
        p = self.source / self.entry["storage_path"]
        p.write_bytes(DATA[:-1])
        with self.assertRaises(mod.ByteAuditBlocked):
            mod.audit(self.load(),self.source,self.target)

    def test_path_traversal_and_windows_drive_rejected(self):
        for path in ("../secret", "claims/../../secret", "C:/secret.txt",
                     "/etc/passwd", "a//b", "a/./b", "a\\b", "a/\x00b"):
            with self.subTest(path=repr(path)):
                with self.assertRaises(mod.ByteAuditBlocked):
                    mod.normalized_storage_path(path)

    def test_duplicate_id_and_target_mapping_rejected(self):
        data=copy.deepcopy(self.entry)
        other=copy.deepcopy(self.entry)
        other["storage_path"]="claims/claim_1/other.pdf"
        for new in ([data,data], [data,other]):
            self.manifest.write_text(json.dumps(new),encoding="utf-8")
            with self.assertRaises(mod.ByteAuditBlocked):
                self.load()

    def test_private_manifest_rejects_unapproved_mime_and_zero_byte(self):
        for field,value in (("mime_type","text/html"),("size_bytes",0),("owner_type","user")):
            entry=copy.deepcopy(self.entry)
            entry[field]=value
            self.manifest.write_text(json.dumps([entry]),encoding="utf-8")
            with self.assertRaises(mod.ByteAuditBlocked):
                self.load()

    def test_source_and_target_must_have_different_roots(self):
        with self.assertRaises(mod.ByteAuditBlocked):
            mod.audit(self.load(),self.source,self.source)

    def test_symlinked_source_object_rejected(self):
        path=self.source / self.entry["storage_path"]
        path.unlink()
        path.symlink_to(self.target / self.entry["storage_path"])
        with self.assertRaises(mod.ByteAuditBlocked):
            mod.audit(self.load(),self.source,self.target)

    def test_missing_target_object_blocks_pair_verification(self):
        (self.target / self.entry["storage_path"]).unlink()
        with self.assertRaises(mod.ByteAuditBlocked):
            mod.audit(self.load(),self.source,self.target)


    def test_frozen_inventory_count_is_mandatory_for_safe_scope(self):
        with self.assertRaises(mod.ByteAuditBlocked):
            mod.audit(self.load(),self.source,self.target,expected_objects=6)
        result=mod.audit(self.load(),self.source,self.target,expected_objects=1,
                         expected_bytes=len(DATA))
        self.assertFalse(result["ready_for_cutover"])

    def test_frozen_total_bytes_detects_incomplete_manifest(self):
        with self.assertRaises(mod.ByteAuditBlocked):
            mod.audit(self.load(),self.source,self.target,expected_objects=1,
                      expected_bytes=len(DATA)+5)

    def test_missing_independent_expected_hash_is_not_marked_verified(self):
        entry=copy.deepcopy(self.entry)
        del entry["expected_sha256"]
        self.manifest.write_text(json.dumps([entry]),encoding="utf-8")
        result=mod.audit(self.load(),self.source,self.target,expected_objects=1,
                         expected_bytes=len(DATA))
        self.assertEqual(result["source_expected_sha256_proofs_verified"],0)
        self.assertTrue(result["source_target_bytes_equal"])
        self.assertFalse(result["ready_for_cutover"])

    def test_source_and_target_sha_proof_requires_no_secret_or_network(self):
        text=SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("--apply",text)
        self.assertNotIn("psycopg",text)
        self.assertNotIn("requests",text)
        self.assertNotIn("http.client",text)
        self.assertIn("hashlib.sha256",text)
        self.assertIn("ready_for_cutover\":False",text)


if __name__=="__main__":
    unittest.main()
