"""Pure, synthetic contract tests: never reads real customer snapshots or secrets."""
import copy
import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "csb_klarin_claim_delta_plan.py"
spec = importlib.util.spec_from_file_location("csb_klarin_claim_delta_plan", SCRIPT)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def fixture():
    target = {"version": 38, "state": {
        "monitoringKlaim": [],
        "uploadBatches": [{"id": "batch-old", "status": "ok"}],
        "auditLogs": [{"id": "audit-old", "action": "read"}],
        "other": {"unchanged": True},
    }}
    source = copy.deepcopy(target)
    source["version"] = 40
    source["state"]["monitoringKlaim"].append({"id": "claim-new", "status": "draft"})
    source["state"]["uploadBatches"].append({"id": "batch-new", "status": "ok"})
    source["state"]["auditLogs"].append({"id": "audit-new", "action": "import"})
    attachment = {"id": "file1", "owner_type": "klaim", "owner_id": "claim-new",
                  "file_name": "synthetic.pdf", "mime_type": "application/pdf",
                  "size_bytes": 64, "object_size_bytes": 64,
                  "storage_path": "sample/claim-new/synthetic.pdf",
                  "blob_sha256": "a" * 64}
    return source, target, [attachment], []


class ClaimDeltaPlannerTests(unittest.TestCase):
    def test_plan_never_reports_ready_to_cutover(self):
        source, target, files, existing = fixture()
        output = mod.plan(source, target, files, existing)
        self.assertEqual(output["mode"], "READ_ONLY_PLAN")
        self.assertFalse(output["ready_for_cutover"])
        self.assertEqual(output["source_only_entries"],
                         {"monitoringKlaim": 1, "uploadBatches": 1, "auditLogs": 1})
        self.assertEqual(output["missing_attachment_metadata"], 1)
        self.assertEqual(output["source_attachment_owners"], 1)
        self.assertEqual(output["total_source_bytes"], 64)
        self.assertEqual(output["unchanged_state_keys"], 1)
        self.assertNotIn("claim-new", str(output))
        self.assertNotIn("synthetic.pdf", str(output))

    def test_same_id_different_content_blocks(self):
        source, target, files, existing = fixture()
        target["state"]["auditLogs"][0]["action"] = "tampered"
        with self.assertRaises(mod.DeltaBlocked):
            mod.plan(source, target, files, existing)

    def test_target_only_business_record_blocks(self):
        source, target, files, existing = fixture()
        target["state"]["monitoringKlaim"].append({"id": "claim-target-only"})
        with self.assertRaises(mod.DeltaBlocked):
            mod.plan(source, target, files, existing)

    def test_unexpected_changes_outside_delta_arrays_block(self):
        source, target, files, existing = fixture()
        target["state"]["other"]["unchanged"] = False
        with self.assertRaises(mod.DeltaBlocked):
            mod.plan(source, target, files, existing)

    def test_attachment_must_belong_to_source_claim(self):
        source, target, files, existing = fixture()
        files[0]["owner_id"] = "unknown-claim"
        with self.assertRaises(mod.DeltaBlocked):
            mod.plan(source, target, files, existing)

    def test_attachment_metadata_size_must_match_storage_record(self):
        source, target, files, existing = fixture()
        files[0]["object_size_bytes"] = 999
        with self.assertRaises(mod.DeltaBlocked):
            mod.plan(source, target, files, existing)

    def test_duplicate_attachment_id_and_path_block(self):
        source, target, files, existing = fixture()
        files.append(copy.deepcopy(files[0]))
        with self.assertRaises(mod.DeltaBlocked):
            mod.plan(source, target, files, existing)

    def test_source_stable_id_collision_blocks(self):
        source, target, files, existing = fixture()
        source["state"]["auditLogs"].append({"id": "audit-old", "action": "duplicate"})
        with self.assertRaises(mod.DeltaBlocked):
            mod.plan(source, target, files, existing)

    def test_equal_versions_with_missing_entries_block(self):
        source, target, files, existing = fixture()
        source["version"] = target["version"]
        with self.assertRaises(mod.DeltaBlocked):
            mod.plan(source, target, files, existing)

    def test_attachment_path_traversal_blocks(self):
        source, target, files, existing = fixture()
        files[0]["storage_path"] = "sample/../customer.pdf"
        with self.assertRaises(mod.DeltaBlocked):
            mod.plan(source, target, files, existing)

    def test_target_metadata_conflict_blocks(self):
        source, target, files, existing = fixture()
        existing.append(copy.deepcopy(files[0]))
        existing[0]["size_bytes"] += 1
        with self.assertRaises(mod.DeltaBlocked):
            mod.plan(source, target, files, existing)

    def test_no_object_byte_proof_marks_no_go(self):
        source, target, files, existing = fixture()
        del files[0]["blob_sha256"]
        output = mod.plan(source, target, files, existing)
        self.assertFalse(output["source_object_bytes_all_attested"])
        self.assertFalse(output["ready_for_cutover"])

    def test_cli_has_no_network_or_write_interface(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("--apply", text)
        self.assertNotIn("psycopg", text)
        self.assertNotIn("urllib", text)
        self.assertNotIn("requests", text)
        self.assertNotIn("database_url", text)
        self.assertIn("READ_ONLY_PLAN", text)


if __name__ == "__main__":
    unittest.main()
