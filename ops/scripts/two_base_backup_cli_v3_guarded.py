#!/usr/bin/env python3
"""Seven pinned Supabase PostgreSQL exports for a private human operator.

DEFAULT: zero network, file reads or writes. Explicit --backup-pg creates
local logical role/schema/data SQL dumps with Supabase CLI v3 and exact
--remote=<project-ref> flags (never the changed default local database).
Use operator's own protected supabase login: no credentials in argv or output.

This does NOT export physical Storage bytes, prove a consistent distributed
snapshot, restore a database, switch Vercel routing, or authorize cutover.
No subprocess output or customer data is ever printed by this wrapper.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

PROJECTS = (
    "fdhqidjltlihzdcbqfrd",  # bbm-finance (target)
    "numlkqppirrxfwdhazja",  # bbm-klarin (target)
    "lmbvbgkqvidtkzxtvtpe",  # csb-finance (legacy)
    "vmpurwykfzcmculnnjfw",  # gpp-piutang-v2 (legacy)
    "loodbfjkskduzqfthxxi",  # gpp-finance-cabang (legacy)
    "krwoiucqfcijmihnrlem",  # csb-klarin (legacy)
    "aupbqpdxiqulxcxeewri",  # gpp-stock (legacy)
)
ARTIFACTS = (
    ("roles.sql", ("--role-only",)),
    ("schema.sql", ()),
    ("data.sql", ("--data-only", "--use-copy",
                  "-x", "storage.buckets_vectors",
                  "-x", "storage.vector_indexes")),
)
HASH = re.compile(r"[a-f0-9]{64}\Z")
NAME = re.compile(r"[a-zA-Z0-9_-]{8,80}\Z")
CLI = re.compile(r"^\s*v?(3)\.(\d+)\.(\d+)(?:[-+][^\s]+)?\s*$")
MAX_MANIFEST_BYTES = 1_000_000
MIN_SQL_BYTES = 20


class BackupBlocked(ValueError):
    """Prevents disclosure of CLI output, private paths and authentication."""


def private_root(raw: str) -> Path:
    root = Path(raw)
    if not root.is_absolute() or root.is_symlink() or not root.is_dir():
        raise BackupBlocked("Preexisting absolute private backup root required")
    resolved = root.resolve(strict=True)
    if os.name == "posix" and resolved.stat().st_mode & 0o077:
        raise BackupBlocked("Private backup root must have mode 0700")
    return resolved


def safe_child(root: Path, components: tuple[str, ...]) -> Path:
    path = root
    for part in components:
        if not NAME.fullmatch(part) and part not in ("roles.sql","schema.sql","data.sql"):
            raise BackupBlocked("Unexpected logical backup artifact name")
        path = path / part
        if path.is_symlink():
            raise BackupBlocked("Symbolic link in protected backup path")
    if not path.resolve(strict=False).is_relative_to(root):
        raise BackupBlocked("Backup path escaped private root")
    return path


def digest_sql(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise BackupBlocked("Missing or symlinked logical export")
    stat_result = path.stat()
    if not stat.S_ISREG(stat_result.st_mode) or stat_result.st_size <= MIN_SQL_BYTES:
        raise BackupBlocked("Logical export missing or suspiciously small")
    if os.name == "posix" and stat_result.st_mode & 0o077:
        raise BackupBlocked("Logical export permissions not private")
    value=hashlib.sha256()
    size=0
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024*1024), b""):
            size += len(block)
            value.update(block)
    if size != stat_result.st_size:
        raise BackupBlocked("Logical export changed during hash verification")
    return {"sha256":value.hexdigest(),"bytes":size}


def cli_major_v3() -> str:
    try:
        result=subprocess.run(["supabase","--version"],capture_output=True,
                              text=True,timeout=20,check=False)
    except (OSError,subprocess.TimeoutExpired):
        raise BackupBlocked("Supabase CLI unavailable") from None
    match=CLI.fullmatch(result.stdout.strip())
    if result.returncode != 0 or match is None:
        raise BackupBlocked("Require reviewed Supabase CLI v3; v2/unknown not accepted")
    return result.stdout.strip()


def backup_command(ref: str, name: str, target: Path) -> list[str]:
    if ref not in PROJECTS or name not in dict(ARTIFACTS):
        raise BackupBlocked("Unpinned project or backup output")
    return (["supabase","db","dump","-f",str(target)]
            + list(dict(ARTIFACTS)[name]) + ["--remote="+ref])


def write_exclusive(path: Path, raw: bytes):
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY
    if hasattr(os,"O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd=os.open(path,flags,0o600)
        with os.fdopen(fd,"wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        raise BackupBlocked("Private backup manifest already exists or cannot be written") from None


def backup_all(args, runner=subprocess.run):
    if (not args.approved_change_ref or not args.approved_change_ref.strip()
        or not args.confirm_private_encrypted
        or not args.confirm_operator_owns_all_seven
        or not args.backup_root):
        raise BackupBlocked("Owner approval, encrypted root and seven-project acknowledgement required")
    root=private_root(args.backup_root)
    version=cli_major_v3()
    stamp=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_name="seven-base-pg-"+stamp
    folder=safe_child(root,(run_name,))
    try:
        folder.mkdir(mode=0o700)
    except FileExistsError:
        raise BackupBlocked("Backup run already exists; never overwrite") from None
    # On POSIX also protect CLI-created exports before they exist.
    previous_mask=os.umask(0o077)
    try:
        inventory=[]
        for ref in PROJECTS:
            project_dir=safe_child(folder,(ref,))
            project_dir.mkdir(mode=0o700)
            artifacts={}
            for filename,_ in ARTIFACTS:
                dest=safe_child(folder,(ref,filename))
                if dest.exists() or dest.is_symlink():
                    raise BackupBlocked("Refusing to overwrite existing SQL file")
                cmd=backup_command(ref,filename,dest)
                try:
                    result=runner(cmd,cwd=folder,capture_output=True,text=True,
                                  timeout=900,check=False)
                except (OSError,subprocess.TimeoutExpired):
                    raise BackupBlocked("Supabase CLI logical export failed or timed out") from None
                if result.returncode != 0:
                    # Never print the CLI's stdout/stderr, which might contain DSNs.
                    raise BackupBlocked("Supabase CLI logical export returned failure") from None
                if os.name=="posix" and dest.exists():
                    dest.chmod(0o600)
                artifacts[filename]=digest_sql(dest)
            inventory.append({"project_ref":ref,"sql":artifacts})
        manifest={
            "format":"GPRO_PG_EXPORT_V3",
            "created_utc":datetime.now(timezone.utc).isoformat(),
            "cli_version":version,
            "project_count":len(PROJECTS),
            "projects":inventory,
            "operator_approved_change_ref":args.approved_change_ref.strip(),
            "snapshot_write_freeze_verified":False,
            "actual_storage_bytes_backed_up":False,
            "independent_isolated_restore_verified":False,
            "cutover_ready":False,
            "delete_or_pause_legacy_projects":False,
        }
        output=json.dumps(manifest,indent=2,sort_keys=True).encode("utf-8")
        write_exclusive(folder/"private-pg-export-manifest.json",output)
        return {
            "mode":"SEVEN_PROJECT_LOCAL_PG_LOGICAL_EXPORT",
            "project_count":len(PROJECTS),
            "sql_file_count":len(PROJECTS)*len(ARTIFACTS),
            "sql_sha256_recorded":True,
            "storage_original_bytes_exported":False,
            "isolated_restore_verified":False,
            "cutover_ready":False,
        }
    finally:
        os.umask(previous_mask)


def verify_private(args):
    root=private_root(args.verify_private)
    path=root/"private-pg-export-manifest.json"
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_MANIFEST_BYTES:
        raise BackupBlocked("Private export manifest missing, oversized or symlinked")
    try:
        inventory=json.loads(path.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,json.JSONDecodeError):
        raise BackupBlocked("Unreadable protected export manifest") from None
    if not isinstance(inventory,dict) or inventory.get("format")!="GPRO_PG_EXPORT_V3":
        raise BackupBlocked("Unknown or incomplete export inventory")
    projects=inventory.get("projects")
    if not isinstance(projects,list) or len(projects)!=7 or inventory.get("project_count")!=7:
        raise BackupBlocked("Exact seven-project export inventory required")
    if (not str(inventory.get("cli_version","")).startswith("3.")
        or inventory.get("cutover_ready") is not False
        or inventory.get("delete_or_pause_legacy_projects") is not False):
        raise BackupBlocked("Backup manifest must remain no-cutover / CLI v3")
    refs=set()
    for entry in projects:
        if not isinstance(entry,dict) or entry.get("project_ref") not in PROJECTS:
            raise BackupBlocked("Unexpected backup project")
        ref=entry["project_ref"]
        if ref in refs:
            raise BackupBlocked("Duplicated project cannot replace missing source")
        refs.add(ref)
        sql=entry.get("sql")
        if not isinstance(sql,dict) or set(sql)!={a for a,_ in ARTIFACTS}:
            raise BackupBlocked("Missing roles/schema/data SQL export")
        for filename,_ in ARTIFACTS:
            expected=sql[filename]
            if not isinstance(expected,dict):
                raise BackupBlocked("Malformed private SQL digest")
            if not HASH.fullmatch(str(expected.get("sha256",""))):
                raise BackupBlocked("SQL SHA-256 proof missing")
            if type(expected.get("bytes")) is not int:
                raise BackupBlocked("Original SQL export byte length missing")
            actual=digest_sql(safe_child(root,(ref,filename)))
            if expected!=actual:
                raise BackupBlocked("SQL export hash or size differs from sealed manifest")
    if refs!=set(PROJECTS):
        raise BackupBlocked("One or more original Supabase project exports missing")
    return {
        "mode":"OFFLINE_PG_EXPORT_SHA256_RECHECK",
        "project_count":7,"sql_file_count":21,
        "pg_sql_integrity_pass":True,
        "snapshot_write_freeze_verified":False,
        "physical_storage_bytes_verified":False,
        "isolated_restore_verified":False,
        "cutover_ready":False,
        "delete_or_pause_legacy_projects":False,
    }


def parser():
    p=argparse.ArgumentParser(description="7→2: private CLI v3 SQL export, never auto-cutover")
    group=p.add_mutually_exclusive_group()
    group.add_argument("--backup-pg",action="store_true")
    group.add_argument("--verify-private",default="",metavar="PRIVATE_RUN_DIR")
    p.add_argument("--backup-root",default="")
    p.add_argument("--approved-change-ref",default="")
    p.add_argument("--confirm-private-encrypted",action="store_true")
    p.add_argument("--confirm-operator-owns-all-seven",action="store_true")
    return p


def main():
    args=parser().parse_args()
    try:
        if args.backup_pg:
            result=backup_all(args)
        elif args.verify_private:
            result=verify_private(args)
        else:
            result={
                "mode":"DEFAULT_NO_NETWORK_NO_FILES",
                "project_count":7,
                "external_cli_calls":0,
                "write_operations":0,
                "required_actions":"approved private SQL export, physical Storage bytes, isolated restore",
                "cutover_ready":False,
            }
        print(json.dumps(result,sort_keys=True))
        return 0
    except Exception:
        # Never expose credentials, CLI raw text, private file paths or customer data.
        print("NO-GO: private seven-project backup proof or CLI v3 target safety failed",
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
