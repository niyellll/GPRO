"""Synthetic safety tests for pinned Supabase CLI v3 seven-project logical exports.

Never connects to actual Supabase, creates real user backups, or reads secrets.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"/"two_base_backup_cli_v3_guarded.py"
spec=importlib.util.spec_from_file_location("two_base_backup_cli_v3_guarded",SCRIPT)
assert spec and spec.loader
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

FAKE_SQL=b"-- Synthetic PostgreSQL SQL dump only --\nSELECT 1;\n"


def synthetic_args(root: Path, **patches):
    values=dict(backup_pg=True,verify_private="",backup_root=str(root),
                approved_change_ref="fake-owner-ticket-test-only",
                confirm_private_encrypted=True,
                confirm_operator_owns_all_seven=True)
    values.update(patches)
    return argparse.Namespace(**values)


class SevenProjectPgBackupV3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"locked-down"
        self.root.mkdir(mode=0o700)

    def synthetic_runner(self,cmd,**kwargs):
        self.assertEqual(cmd[:3],["supabase","db","dump"])
        self.assertEqual(cmd[-1][:9],"--remote=")
        self.assertNotIn("--yes",cmd)
        self.assertNotIn("--linked",cmd)
        self.assertNotIn("--db-url",cmd)
        self.assertNotIn("--local",cmd)
        self.assertNotIn("--password",cmd)
        self.assertEqual(len([x for x in cmd if x.startswith("--remote=")]),1)
        self.assertIn(cmd[-1][9:],mod.PROJECTS)
        path=Path(cmd[cmd.index("-f")+1])
        self.assertTrue(path.is_relative_to(self.root))
        self.assertFalse(path.exists())
        path.write_bytes(FAKE_SQL)
        return subprocess.CompletedProcess(cmd,0,stdout="",stderr="")

    def test_no_network_no_file_default(self):
        proc=subprocess.run([sys.executable,str(SCRIPT)],capture_output=True,
                            text=True,check=False,timeout=10)
        self.assertEqual(proc.returncode,0,proc.stderr)
        result=json.loads(proc.stdout)
        self.assertEqual(result["external_cli_calls"],0)
        self.assertEqual(result["write_operations"],0)
        self.assertFalse(result["cutover_ready"])

    def test_exactly_two_destinations_and_five_sources(self):
        self.assertEqual(len(mod.PROJECTS),7)
        self.assertEqual(len(set(mod.PROJECTS)),7)
        self.assertEqual(mod.PROJECTS[:2],
                         ("fdhqidjltlihzdcbqfrd","numlkqppirrxfwdhazja"))
        self.assertEqual(len(mod.PROJECTS[2:]),5)
        self.assertEqual({key for key,_ in mod.ARTIFACTS},
                         {"roles.sql","schema.sql","data.sql"})

    def test_dump_commands_explicit_project_and_never_local(self):
        for ref in mod.PROJECTS:
            for name,_ in mod.ARTIFACTS:
                cmd=mod.backup_command(ref,name,self.root/name)
                self.assertEqual(cmd[-1],"--remote="+ref)
                self.assertEqual(cmd[:3],["supabase","db","dump"])
                self.assertNotIn("--db-url",cmd)
                self.assertNotIn("--linked",cmd)
        with self.assertRaises(mod.BackupBlocked):
            mod.backup_command("not-approved","roles.sql",self.root/"roles.sql")
        with self.assertRaises(mod.BackupBlocked):
            mod.backup_command(mod.PROJECTS[0],"backup.sql",self.root/"backup.sql")

    def test_v3_strict_major_version(self):
        for version in ("2.123.1","4.0.0","local","3.0.0\nextra"):
            with patch.object(mod.subprocess,"run",return_value=subprocess.CompletedProcess(
                        ["supabase","--version"],0,stdout=version,stderr="")):
                with self.assertRaises(mod.BackupBlocked):
                    mod.cli_major_v3()
        with patch.object(mod.subprocess,"run",return_value=subprocess.CompletedProcess(
                    ["supabase","--version"],0,stdout="3.2.0\n",stderr="")):
            self.assertEqual(mod.cli_major_v3(),"3.2.0")

    def test_export_requires_approval_and_private_root(self):
        for alteration in (
            {"approved_change_ref":""},
            {"confirm_private_encrypted":False},
            {"confirm_operator_owns_all_seven":False},
            {"backup_root":""},
        ):
            with self.subTest(alteration=alteration):
                with self.assertRaises(mod.BackupBlocked):
                    mod.backup_all(synthetic_args(self.root,**alteration),
                                   runner=self.synthetic_runner)
        public=Path(self.tmp.name)
        if os.name=="posix":
            with self.assertRaises(mod.BackupBlocked):
                mod.private_root(str(public))

    def test_synthetic_21_sql_dumps_and_offline_integrity(self):
        with patch.object(mod,"cli_major_v3",return_value="3.2.0"):
            summary=mod.backup_all(synthetic_args(self.root),
                                   runner=self.synthetic_runner)
        self.assertEqual(summary["sql_file_count"],21)
        self.assertFalse(summary["storage_original_bytes_exported"])
        self.assertFalse(summary["isolated_restore_verified"])
        runs=list(self.root.iterdir())
        self.assertEqual(len(runs),1)
        report=mod.verify_private(argparse.Namespace(verify_private=str(runs[0])))
        self.assertTrue(report["pg_sql_integrity_pass"])
        self.assertEqual(report["project_count"],7)
        self.assertFalse(report["cutover_ready"])
        manifest=json.loads((runs[0]/"private-pg-export-manifest.json").read_text())
        self.assertEqual(len(manifest["projects"]),7)
        self.assertEqual(manifest["projects"][0]["sql"]["schema.sql"]["sha256"],
                         hashlib.sha256(FAKE_SQL).hexdigest())
        self.assertFalse(manifest["independent_isolated_restore_verified"])

    def test_modified_content_fails_no_false_positive(self):
        with patch.object(mod,"cli_major_v3",return_value="3.2.0"):
            mod.backup_all(synthetic_args(self.root),runner=self.synthetic_runner)
        run=next(self.root.iterdir())
        source=run/mod.PROJECTS[3]/"data.sql"
        source.write_bytes(FAKE_SQL+b"extra")
        with self.assertRaises(mod.BackupBlocked):
            mod.verify_private(argparse.Namespace(verify_private=str(run)))

    def test_missing_source_cannot_be_replaced_by_duplicate_target(self):
        with patch.object(mod,"cli_major_v3",return_value="3.2.0"):
            mod.backup_all(synthetic_args(self.root),runner=self.synthetic_runner)
        run=next(self.root.iterdir())
        file=run/"private-pg-export-manifest.json"
        manifest=json.loads(file.read_text())
        manifest["projects"][-1]=dict(manifest["projects"][0])
        file.write_text(json.dumps(manifest),encoding="utf-8")
        with self.assertRaises(mod.BackupBlocked):
            mod.verify_private(argparse.Namespace(verify_private=str(run)))

    def test_manifest_cannot_self_authorize_deletion(self):
        with patch.object(mod,"cli_major_v3",return_value="3.2.0"):
            mod.backup_all(synthetic_args(self.root),runner=self.synthetic_runner)
        run=next(self.root.iterdir())
        file=run/"private-pg-export-manifest.json"
        m=json.loads(file.read_text())
        m["cutover_ready"]=True
        file.write_text(json.dumps(m),encoding="utf-8")
        with self.assertRaises(mod.BackupBlocked):
            mod.verify_private(argparse.Namespace(verify_private=str(run)))

    def test_reject_symlinked_dump_and_root(self):
        if not hasattr(os,"symlink"):
            self.skipTest("No symlink support")
        with patch.object(mod,"cli_major_v3",return_value="3.2.0"):
            mod.backup_all(synthetic_args(self.root),runner=self.synthetic_runner)
        run=next(self.root.iterdir())
        file=run/mod.PROJECTS[0]/"data.sql"
        file.unlink()
        try:
            file.symlink_to(run/mod.PROJECTS[1]/"data.sql")
        except OSError:
            self.skipTest("Current OS denies creating symlinks")
        with self.assertRaises(mod.BackupBlocked):
            mod.verify_private(argparse.Namespace(verify_private=str(run)))

    def test_failed_cli_export_fails_closed_without_manifest(self):
        calls=[]
        def failing_runner(cmd,**kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd,1,stdout="confidential",stderr="private-password")
        with patch.object(mod,"cli_major_v3",return_value="3.2.0"):
            with self.assertRaises(mod.BackupBlocked):
                mod.backup_all(synthetic_args(self.root),runner=failing_runner)
        self.assertEqual(len(calls),1)
        self.assertEqual(len(list(self.root.rglob("private-pg-export-manifest.json"))),0)

    def test_cli_source_guards_do_not_touch_production_ddl(self):
        text=SCRIPT.read_text()
        for forbidden in (
            "supabase db push","supabase db reset","supabase storage rm",
            "DROP PROJECT","DELETE FROM","ALTER ROLE","DROP SCHEMA",
            "pause_project","remove_project",
        ):
            self.assertNotIn(forbidden,text)


if __name__=="__main__":
    unittest.main()
