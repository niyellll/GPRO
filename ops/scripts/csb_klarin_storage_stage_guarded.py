#!/usr/bin/env python3
"""Stage original private CSB Klarin Storage bytes between pinned Supabase projects.

Default: OFFLINE DRY RUN only (no HTTP, no file I/O beyond private manifest).
Apply: operator-attested backup restore + freeze + complete 6-object SHA256
manifest + two *distinct* server-only Supabase credentials in environment.

Does NOT copy database state or cut over app traffic; never delete or upsert
an existing object. Storage is not transactionally coupled to Postgres:
on failure, previously staged target files remain for explicit review.
Never run in CI with real secrets, and never put manifests/bytes in GitHub.
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
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import (
    build_opener, HTTPRedirectHandler, HTTPSHandler, Request,
)

from csb_klarin_storage_byte_audit import (
    ByteAuditBlocked, audit, private_manifest, verified_local_root,
)

SOURCE_REF = "krwoiucqfcijmihnrlem"
TARGET_REF = "numlkqppirrxfwdhazja"
SOURCE_BUCKET = "klarin-private-attachments"
TARGET_BUCKET = "gpro-csb-private-attachments"
SOURCE_SECRET = "GPRO_CSB_KLARIN_SOURCE_STORAGE_SERVICE_KEY"
TARGET_SECRET = "GPRO_CSB_KLARIN_TARGET_STORAGE_SERVICE_KEY"
SHA_PATTERN = re.compile(r"[0-9a-fA-F]{64}\Z")
KEY_PATTERN = re.compile(r"[A-Za-z0-9._-]{32,8192}\Z")


class StageBlocked(ValueError):
    """No-go. Deliberately avoid file paths, credentials or private IDs."""


class RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise StageBlocked("Storage redirect forbidden")


def storage_url(project_ref: str, bucket: str, path: str, *, private_read: bool) -> str:
    valid = (
        (project_ref == SOURCE_REF and bucket == SOURCE_BUCKET and private_read)
        or (project_ref == TARGET_REF and bucket == TARGET_BUCKET)
    )
    if not valid:
        raise StageBlocked("Project, bucket or Storage operation not allowlisted")
    from csb_klarin_storage_byte_audit import normalized_storage_path
    normalized = normalized_storage_path(path)
    route = "object/authenticated" if private_read else "object"
    return (
        f"https://{project_ref}.supabase.co/storage/v1/{route}/"
        f"{bucket}/{quote(normalized, safe='/')}"
    )


def approval_gate(args) -> None:
    if not args.apply:
        return
    if not all((
        args.approved_change_ref.strip(),
        args.verified_restore_ref.strip(),
        args.frozen_inventory_ref.strip(),
        args.confirm_frozen_writes,
    )):
        raise StageBlocked("Operator-attested approval, restored backup and freeze required")
    if any(
        SHA_PATTERN.fullmatch(getattr(args, key, "")) is None
        for key in ("source_state_sha256", "target_state_sha256")
    ):
        raise StageBlocked("Source and target frozen state SHA256 required")
    if not args.source_root or not args.target_root:
        raise StageBlocked("Two separate encrypted private local file roots required")


def service_tokens(env: dict[str, str]) -> tuple[str, str]:
    source = env.get(SOURCE_SECRET, "")
    target = env.get(TARGET_SECRET, "")
    if (
        not KEY_PATTERN.fullmatch(source)
        or not KEY_PATTERN.fullmatch(target)
        or source == target
    ):
        raise StageBlocked("Two distinct valid server-only Storage keys required")
    return source, target


def manifest_gate(manifest, expected_objects: int, expected_bytes: int):
    if expected_objects < 1 or expected_bytes < 1:
        raise StageBlocked("Frozen object count and bytes must be positive")
    if len(manifest) != expected_objects:
        raise StageBlocked("Private manifest count mismatches frozen source inventory")
    if sum(item["size_bytes"] for item in manifest) != expected_bytes:
        raise StageBlocked("Private manifest bytes mismatch frozen source inventory")
    if any(
        not item.get("expected_sha256")
        or SHA_PATTERN.fullmatch(item["expected_sha256"]) is None
        or item["_source_path"] != item["_target_path"]
        for item in manifest
    ):
        raise StageBlocked("Independent SHA-256 and identical Storage keys required")
    return len(manifest)


def require_private_root(path: Path) -> Path:
    root = verified_local_root(path)
    if os.name == "posix" and root.stat().st_mode & 0o077:
        raise StageBlocked("Private object root must be chmod 700")
    return root


def save_exclusive_or_matching(root: Path, relative: str, data: bytes, digest: str):
    """Keep readback files 0600 and never overwrite a previous snapshot."""
    from csb_klarin_storage_byte_audit import normalized_storage_path
    parts = normalized_storage_path(relative).split("/")
    directory = root
    for name in parts[:-1]:
        directory = directory / name
        if directory.is_symlink():
            raise StageBlocked("Private subdirectory symlink forbidden")
        if not directory.exists():
            directory.mkdir(mode=0o700)
        if not directory.is_dir() or (os.name == "posix" and directory.stat().st_mode & 0o077):
            raise StageBlocked("Private subdirectory must be chmod 700")
    dest = directory / parts[-1]
    if dest.is_symlink():
        raise StageBlocked("Local file symlink forbidden")
    if dest.exists():
        if not dest.is_file() or dest.stat().st_size != len(data):
            raise StageBlocked("Existing private file is not identical")
        from csb_klarin_storage_byte_audit import read_secure_blob
        if read_secure_blob(root, relative, len(data)) != digest:
            raise StageBlocked("Existing private file SHA-256 differs")
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(dest, flags, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        raise StageBlocked("Could not save private readback safely") from None


class StorageHttp:
    """HTTPS only; redirects disabled; no log of signed URLs or response bodies."""

    def __init__(self):
        self.opener = build_opener(RejectRedirects(), HTTPSHandler())

    def request(self, method: str, url: str, key: str, *,
                data: bytes | None = None, content_type: str | None = None,
                maximum_bytes: int = 0):
        if not url.startswith(("https://" + SOURCE_REF + ".supabase.co/",
                               "https://" + TARGET_REF + ".supabase.co/")):
            raise StageBlocked("Unexpected Storage HTTPS endpoint")
        headers = {"apikey": key, "Authorization": "Bearer " + key}
        if method == "POST":
            headers["Content-Type"] = content_type or "application/octet-stream"
            headers["x-upsert"] = "false"
        req = Request(url, headers=headers, data=data, method=method)
        try:
            with self.opener.open(req, timeout=30) as response:
                if method == "GET":
                    result = response.read(maximum_bytes + 1)
                    if len(result) > maximum_bytes:
                        raise StageBlocked("Storage response exceeds approved length")
                    return result
                if response.status not in (200, 201):
                    raise StageBlocked("Storage upload acknowledgement invalid")
                return b""
        except HTTPError as exc:
            if method == "GET" and exc.code == 404:
                return None
            raise StageBlocked("Storage operation denied or failed") from None
        except (URLError, TimeoutError, OSError):
            raise StageBlocked("Storage HTTPS transport failed") from None


def stage_objects(manifest, expected_bytes: int, source_root: Path, target_root: Path,
                  source_key: str, target_key: str, transport) -> dict:
    source_root = require_private_root(source_root)
    target_root = require_private_root(target_root)
    if source_root == target_root:
        raise StageBlocked("Source and target private roots must differ")
    uploaded = reused = 0
    for entry in manifest:
        path = entry["_source_path"]
        limit = entry["size_bytes"]
        digest = entry["expected_sha256"].lower()
        source_url = storage_url(SOURCE_REF, SOURCE_BUCKET, path, private_read=True)
        target_read = storage_url(TARGET_REF, TARGET_BUCKET, path, private_read=True)
        target_write = storage_url(TARGET_REF, TARGET_BUCKET, path, private_read=False)

        raw = transport.request("GET", source_url, source_key, maximum_bytes=limit)
        if raw is None or len(raw) != limit or hashlib.sha256(raw).hexdigest() != digest:
            raise StageBlocked("Original private Storage bytes failed frozen SHA256 proof")
        save_exclusive_or_matching(source_root, path, raw, digest)

        existing = transport.request("GET", target_read, target_key, maximum_bytes=limit)
        if existing is None:
            transport.request("POST", target_write, target_key,
                              data=raw, content_type=entry["mime_type"])
            uploaded += 1
            existing = transport.request("GET", target_read, target_key,
                                         maximum_bytes=limit)
        else:
            reused += 1
        if existing is None or len(existing) != limit or hashlib.sha256(existing).hexdigest() != digest:
            raise StageBlocked("Target private Storage readback failed SHA256 proof")
        save_exclusive_or_matching(target_root, path, existing, digest)

    proof = audit(manifest, source_root, target_root,
                  expected_objects=len(manifest), expected_bytes=expected_bytes)
    if (not proof["source_target_bytes_equal"]
        or proof["source_expected_sha256_proofs_verified"] != len(manifest)):
        raise StageBlocked("Final independent local source/target byte audit failed")
    return {
        "mode": "OPERATOR_ATTESTED_STORAGE_STAGING",
        "objects": len(manifest),
        "bytes": expected_bytes,
        "objects_uploaded": uploaded,
        "objects_reused_after_sha256": reused,
        "verified_source_and_target_sha256": True,
        "ready_for_cutover": False,
        "still_requires": "DB metadata/state CAS, authenticated private-file app E2E, full backup and rollback signoff",
    }


def cli():
    p = argparse.ArgumentParser(
        description="Private CSB Klarin file-byte staging; offline dry-run by default"
    )
    p.add_argument("--manifest", required=True)
    p.add_argument("--expected-objects", required=True, type=int)
    p.add_argument("--expected-total-bytes", required=True, type=int)
    p.add_argument("--source-root", default="")
    p.add_argument("--target-root", default="")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--approved-change-ref", default="")
    p.add_argument("--verified-restore-ref", default="")
    p.add_argument("--frozen-inventory-ref", default="")
    p.add_argument("--confirm-frozen-writes", action="store_true")
    p.add_argument("--source-state-sha256", default="")
    p.add_argument("--target-state-sha256", default="")
    return p


def main() -> int:
    args = cli().parse_args()
    try:
        manifest = private_manifest(Path(args.manifest))
        manifest_gate(manifest, args.expected_objects, args.expected_total_bytes)
        approval_gate(args)
        if not args.apply:
            print(json.dumps({
                "mode": "OFFLINE_DRY_RUN", "objects": len(manifest),
                "bytes": args.expected_total_bytes, "network_calls": 0,
                "write_operations": 0, "ready_for_cutover": False,
            }, sort_keys=True))
            return 0
        source_key, target_key = service_tokens(os.environ)
        result = stage_objects(
            manifest, args.expected_total_bytes, Path(args.source_root),
            Path(args.target_root), source_key, target_key, StorageHttp()
        )
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ByteAuditBlocked, StageBlocked, ValueError, OSError):
        print("NO-GO: private Storage stage proof, credentials, path, or release gate failed",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
