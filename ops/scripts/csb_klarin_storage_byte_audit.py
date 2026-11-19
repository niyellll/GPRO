#!/usr/bin/env python3
"""Offline, byte-level CSB Klarin Storage verification. NEVER uploads or writes.

The operator exports private source objects from the legacy Supabase bucket and,
after a separately authorized move, private target objects into separate local
roots preserving paths. NEVER put originals, manifests, IDs, hashes, or secrets
in GitHub or chat. This tool prints aggregates only, never raw filenames.
Manifest format is documented in the CSB Klarin NO-GO runbook.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

ALLOWED_MIME = frozenset((
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
))
MAX_MANIFEST_SIZE = 512 * 1024
MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_ENTRIES = 10000


class ByteAuditBlocked(ValueError):
    """The operator must investigate in a private environment."""


def private_manifest(path: Path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MANIFEST_SIZE:
        raise ByteAuditBlocked("Private manifest missing, symlinked or oversized")
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise ByteAuditBlocked("Private manifest is not valid JSON") from None
    if not isinstance(content, list) or not 1 <= len(content) <= MAX_ENTRIES:
        raise ByteAuditBlocked("Private manifest must have 1..10000 objects")
    ids, paths, owners_and_names = set(), set(), set()
    for entry in content:
        if not isinstance(entry, dict):
            raise ByteAuditBlocked("Private manifest has non-object row")
        for k in ("id", "owner_type", "owner_id", "file_name", "storage_path", "mime_type"):
            if not isinstance(entry.get(k), str) or not entry[k]:
                raise ByteAuditBlocked("Private manifest has missing identity or path metadata")
        if entry["owner_type"] != "klaim" or entry["mime_type"] not in ALLOWED_MIME:
            raise ByteAuditBlocked("Private manifest has unknown owner kind or MIME")
        size = entry.get("size_bytes")
        if type(size) is not int or not 1 <= size <= MAX_FILE_SIZE:
            raise ByteAuditBlocked("Private manifest has invalid object size")
        src_path = normalized_storage_path(entry["storage_path"])
        dst_path = normalized_storage_path(entry.get("target_storage_path",src_path))
        name_key = (entry["owner_type"],entry["owner_id"],entry["file_name"])
        if entry["id"] in ids or src_path in paths or name_key in owners_and_names:
            raise ByteAuditBlocked("Duplicate ID, source path or owner filename in manifest")
        ids.add(entry["id"])
        paths.add(src_path)
        owners_and_names.add(name_key)
        expected_hash = entry.get("expected_sha256")
        if expected_hash is not None and (
            not isinstance(expected_hash, str)
            or re.fullmatch("[0-9a-fA-F]{64}", expected_hash) is None
        ):
            raise ByteAuditBlocked("Manifest contains malformed expected SHA-256")
        entry["_source_path"] = src_path
        entry["_target_path"] = dst_path
    if len({e["_target_path"] for e in content}) != len(content):
        raise ByteAuditBlocked("Multiple source objects map to the same target object")
    return content


def normalized_storage_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ByteAuditBlocked("Invalid Storage path")
    if (
        value.startswith("/") or "\\" in value or ":" in value
        or any(not p or p in (".","..") for p in value.split("/"))
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    ):
        raise ByteAuditBlocked("Unsafe Storage path")
    return value


def verified_local_root(root: Path) -> Path:
    if root.is_symlink() or not root.is_dir():
        raise ByteAuditBlocked("Object root missing or symbolic link")
    return root.resolve(strict=True)


def read_secure_blob(root: Path, relative_path: str, expected_bytes: int) -> str:
    root = verified_local_root(root)
    parts = relative_path.split("/")
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise ByteAuditBlocked("Object contains a symbolic link")
    if not path.is_file() or not path.resolve(strict=True).is_relative_to(root):
        raise ByteAuditBlocked("Object missing, not a regular file or outside private root")
    size = path.stat().st_size
    if size != expected_bytes:
        raise ByteAuditBlocked("Object byte length does not match metadata")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(path, flags)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size != expected_bytes:
                raise ByteAuditBlocked("Object is not a regular file or size changed")
            digest = hashlib.sha256()
            with os.fdopen(fd,"rb",closefd=False) as blob:
                for chunk in iter(lambda: blob.read(1024 * 1024), b""):
                    digest.update(chunk)
            return digest.hexdigest()
        finally:
            os.close(fd)
    except OSError:
        raise ByteAuditBlocked("Unable to inspect private object") from None


def audit(manifest, source_root: Path, target_root: Path | None = None,
          expected_objects: int | None = None, expected_bytes: int | None = None):
    if expected_objects is not None and len(manifest) != expected_objects:
        raise ByteAuditBlocked("Manifest object count differs from frozen inventory")
    total_expected = sum(entry["size_bytes"] for entry in manifest)
    if expected_bytes is not None and total_expected != expected_bytes:
        raise ByteAuditBlocked("Manifest total size differs from frozen inventory")
    source_root = verified_local_root(source_root)
    if target_root is not None:
        target_root = verified_local_root(target_root)
        if target_root == source_root:
            raise ByteAuditBlocked("Source and target local roots must be different")
    bytes_total = 0
    trusted_sha_proofs = 0
    for entry in manifest:
        length = entry["size_bytes"]
        digest = read_secure_blob(source_root, entry["_source_path"], length)
        expected = entry.get("expected_sha256")
        if expected is not None:
            if digest != expected.lower():
                raise ByteAuditBlocked("Source file hash differs from trusted manifest proof")
            trusted_sha_proofs += 1
        if target_root is not None:
            target_hash = read_secure_blob(target_root, entry["_target_path"], length)
            if digest != target_hash:
                raise ByteAuditBlocked("Source/target Storage object SHA-256 mismatch")
        bytes_total += length
    return {
        "mode":"OFFLINE_BYTE_AUDIT",
        "objects":len(manifest),
        "bytes_checked":bytes_total,
        "source_file_lengths_verified":True,
        "source_sha256_digests_computed":len(manifest),
        "source_expected_sha256_proofs_verified":trusted_sha_proofs,
        "source_target_bytes_equal":target_root is not None,
        "ready_for_cutover":False,
        "still_requires":"approved full DB and Storage restore, freeze, role E2E, atomic metadata/state cutover",
    }


def main() -> int:
    p=argparse.ArgumentParser(description="CSB Klarin offline source/target object SHA-256 audit; no writes")
    p.add_argument("--manifest",required=True)
    p.add_argument("--source-root",required=True)
    p.add_argument("--target-root",help="Optional separately exported target tree; omission verifies source bytes only")
    p.add_argument("--expected-objects",required=True,type=int,
                   help="Exact count obtained from fresh, write-frozen source inventory")
    p.add_argument("--expected-total-bytes",required=True,type=int,
                   help="Exact total size obtained from fresh, write-frozen source inventory")
    args=p.parse_args()
    try:
        if args.expected_objects < 1 or args.expected_total_bytes < 1:
            raise ByteAuditBlocked("Expected object count and bytes must be positive")
        summary=audit(private_manifest(Path(args.manifest)),
                      Path(args.source_root),
                      Path(args.target_root) if args.target_root else None,
                      expected_objects=args.expected_objects,
                      expected_bytes=args.expected_total_bytes)
        print(json.dumps(summary,sort_keys=True,indent=2))
        return 0
    except (ByteAuditBlocked,OSError):
        print("NO-GO: private object manifest, byte length, SHA-256 or path check failed",file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
