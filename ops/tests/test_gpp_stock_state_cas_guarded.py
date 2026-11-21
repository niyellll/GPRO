"""Synthetic/offline GPP Pusat state CAS guard tests: no live network or secrets."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"gpp_stock_state_cas_guarded.py"
sys.path.insert(0,str(SCRIPT.parent))
spec=importlib.util.spec_from_file_location("gpp_stock_state_cas_guarded",SCRIPT)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def approved(**changes):
    d=dict(
        live=True,apply=True,approved_change_ref="operator-approved-change",
        verified_restore_ref="actual-full-seven-project-isolated-restore",
        confirm_frozen_writes=True,source_version=6,target_version=4,
        source_sha256="a"*64,target_sha256="b"*64,
        cabang_version=1,cabang_sha256="c"*64,
        expected_attachments=2,expected_total_bytes=100,
        manifest="/approved/gpp-private.json",source_root="/local/src",
        target_root="/local/target",
    )
    d.update(changes)
    return argparse.Namespace(**d)


def state(claim_ids=(),audit_ids=(),batches=()):
    return {"monitoringKlaim":[{"id":x} for x in claim_ids],
            "auditLogs":[{"id":x} for x in audit_ids],
            "uploadBatches":[{"id":x} for x in batches],
            "masterBarang":[{"id":"keep"}]}


class FakeCursor:
    def __init__(self,rows):
        self.rows=rows
        self.executed=[]
    def execute(self,q,p=None):
        self.executed.append((q,p))
    def fetchone(self):
        return self.rows.pop(0) if self.rows else None
    def fetchall(self):
        return self.rows


class GppStockStateCasTests(unittest.TestCase):
    def test_default_does_not_connect_even_if_env_missing(self):
        result=subprocess.run([sys.executable,str(SCRIPT)],text=True,
                              capture_output=True,timeout=10,check=False)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("OFFLINE NO-NETWORK",result.stdout)
        self.assertNotIn("password",result.stdout.lower())

    def test_only_pinned_source_target_and_gpp_pusat(self):
        self.assertEqual(mod.SOURCE_REF,"aupbqpdxiqulxcxeewri")
        self.assertEqual(mod.TARGET_REF,"numlkqppirrxfwdhazja")
        self.assertEqual(mod.SOURCE_BUCKET,"gpp-klarin-attachments")
        self.assertEqual(mod.TARGET_BUCKET,"gpro-gpp-private-attachments")
        self.assertEqual(mod.WORKSPACE,"gpp_pusat")
        self.assertEqual(mod.UNCHANGED_WORKSPACE,"gpp_cabang")

    def test_apply_requires_signed_restore_freeze_and_exact_sha(self):
        mod.approval(approved())
        for bad in (
            {"live":False},{"verified_restore_ref":""},
            {"approved_change_ref":""},{"confirm_frozen_writes":False},
            {"source_version":0},{"target_version":0},{"cabang_version":0},
            {"source_sha256":"not_sha"},{"target_sha256":""},
            {"cabang_sha256":"bad"},{"expected_attachments":0},
            {"expected_total_bytes":0},{"manifest":""},
            {"source_root":""},{"target_root":""},
        ):
            with self.subTest(bad=bad),self.assertRaises(mod.GppStateBlocked):
                mod.approval(approved(**bad))
        mod.approval(approved(apply=False,live=True,verified_restore_ref=""))

    def test_source_state_subset_additive_and_preserves_other_keys(self):
        from csb_klarin_claim_delta_plan import (
            state_delta,merged_state_from_verified_subset,DeltaBlocked,
        )
        src={"version":6,"state":state(
            [f"claim{i}" for i in range(8)],["a0","a1","a2"],["batch1"])}
        dst={"version":4,"state":state([],["a0"],[])}
        result, missing=state_delta(src,dst)
        self.assertEqual(result["source_only_entries"]["monitoringKlaim"],8)
        self.assertEqual(result["source_only_entries"]["auditLogs"],2)
        self.assertEqual(result["source_only_entries"]["uploadBatches"],1)
        self.assertEqual(len(missing),8)
        self.assertEqual(merged_state_from_verified_subset(src,dst),src["state"])
        conflict={"version":4,"state":state([],["foreign-audit"],[])}
        with self.assertRaises(DeltaBlocked):
            state_delta(src,conflict)
        nonclaim={"version":4,"state":state([],["a0"],[])}
        nonclaim["state"]["masterBarang"]=[{"id":"changed"}]
        with self.assertRaises(DeltaBlocked):
            state_delta(src,nonclaim)

    def test_foreign_workspace_attachment_is_blocked(self):
        cursor=FakeCursor([[{"id":"synthetic","workspace_key":"gpp_cabang",
                            "owner_type":"klaim"}]])
        with self.assertRaises(mod.GppStateBlocked):
            mod.attachment_rows(cursor,"gpp_stock")
        self.assertIn("ORDER BY id",cursor.executed[0][0])

    def test_original_metadata_identity_ignores_only_migration_timestamp(self):
        one={k:None for k in mod.COLUMNS}
        one["workspace_key"]="gpp_pusat"
        another=dict(one,storage_migrated_at="new-event")
        self.assertTrue(mod.metadata_matches(one,another))
        another["owner_id"]="other-claim"
        self.assertFalse(mod.metadata_matches(one,another))

    def test_missing_cabang_snapshot_fails_closed(self):
        sc=FakeCursor([None])
        tc=FakeCursor([{"version":1}])
        with self.assertRaises(mod.GppStateBlocked):
            mod.cabang_guard(sc,tc,approved())
        self.assertIn("gpp_cabang",str(sc.executed[0][1]))

    def test_owner_and_workspace_are_enforced_by_cas_source(self):
        code=SCRIPT.read_text(encoding="utf-8")
        self.assertIn("BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE",code)
        self.assertIn("LOCK TABLE gpp_stock.klarin_stock_claim_attachments",code)
        self.assertIn("FOR UPDATE",code)
        self.assertIn("WHERE workspace_key=%s AND version=%s AND state=%s::jsonb",code)
        self.assertIn('tc.fetchone()["role"]!="postgres"',code)
        self.assertIn("gpro_csb_klarin",code)
        self.assertIn("UPDATE gpp_stock.klarin_stock_claim_app_state",code)
        self.assertNotIn("UPDATE gpp_stock.users",code)
        self.assertNotIn("DELETE FROM",code)

    def test_private_file_proof_passes_only_for_original_and_target_matching(self):
        blob=b"%PDF-1.7 - FAKE GPP FILE - SYNTHETIC ONLY"
        size=len(blob)
        digest=hashlib.sha256(blob).hexdigest()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            (root/"source").mkdir(mode=0o700)
            (root/"target").mkdir(mode=0o700)
            for sub in ("source","target"):
                (root/sub/"sample.pdf").write_bytes(blob)
            a=approved(expected_attachments=1,expected_total_bytes=size,
                       source_root=str(root/"source"),
                       target_root=str(root/"target"),
                       manifest=str(root/"manifest.json"))
            entry={"id":"s1","workspace_key":"gpp_pusat","owner_type":"klaim",
                   "owner_id":"claim1","file_name":"sample.pdf","mime_type":"application/pdf",
                   "size_bytes":size,"storage_path":"sample.pdf",
                   "expected_sha256":digest}
            (root/"manifest.json").write_text(json.dumps([entry]),encoding="utf-8")
            meta=[dict(entry,data_base64="",uploaded_by="tester",created_at=None,
                       storage_migrated_at=None)]
            mod.validate_manifest(a,meta)
            entry["workspace_key"]="gpp_cabang"
            (root/"manifest.json").write_text(json.dumps([entry]),encoding="utf-8")
            with self.assertRaises(mod.GppStateBlocked):
                mod.validate_manifest(a,meta)

if __name__=="__main__":
    unittest.main()
