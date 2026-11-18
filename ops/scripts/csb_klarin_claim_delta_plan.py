#!/usr/bin/env python3
"""CSB Klarin business delta planning ONLY: never connects to a DB or writes data.

Accept private, securely exported JSON snapshots of the *same* frozen checkpoint.
Files may contain customer/business data: use an encrypted ephemeral workstation.
NEVER commit input files or redirect their raw contents to CI/logs.
Only aggregate counts, versions and status are printed. No transfer/--apply exists.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

DELTA_KEYS = ("monitoringKlaim", "uploadBatches", "auditLogs")
EXPECTED_OWNER = "klaim"
MIME_ALLOWLIST = frozenset((
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
))
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024


class DeltaBlocked(ValueError):
    """Fail closed without leaking record contents to error logs."""


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def safe_id(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DeltaBlocked("JSON row has missing or invalid stable id")
    return value


def validate_state(snapshot: object) -> tuple[int, dict]:
    if not isinstance(snapshot, dict):
        raise DeltaBlocked("State snapshot must be a JSON object")
    version = snapshot.get("version")
    state = snapshot.get("state")
    if type(version) is not int or version < 1 or not isinstance(state, dict):
        raise DeltaBlocked("State snapshot version/state invalid")
    if any(key not in state for key in DELTA_KEYS):
        raise DeltaBlocked("One or more required claim-state keys missing")
    return version, state


def id_records(value: object, key: str) -> dict[str, str]:
    if not isinstance(value, list):
        raise DeltaBlocked("State delta is not an array: " + key)
    result = {}
    for entry in value:
        if not isinstance(entry, dict):
            raise DeltaBlocked("State array has a non-object entry: " + key)
        id_value = safe_id(entry.get("id"))
        if id_value in result:
            raise DeltaBlocked("Duplicate stable business ID within " + key)
        result[id_value] = fingerprint(entry)
    return result


def state_delta(source: object, target: object) -> tuple[dict, set[str]]:
    source_version, src = validate_state(source)
    target_version, dst = validate_state(target)
    if source_version < target_version:
        raise DeltaBlocked("Target state is newer than source; manual conflict review")
    if set(src) != set(dst):
        raise DeltaBlocked("State key inventory differs across source and target")
    unchanged = [k for k in src if k not in DELTA_KEYS]
    for key in unchanged:
        if fingerprint(src[key]) != fingerprint(dst[key]):
            raise DeltaBlocked("Unapproved differences in unaffected state keys")
    added_claim_ids = set()
    deltas = {}
    for key in DELTA_KEYS:
        src_by_id = id_records(src[key], key)
        dst_by_id = id_records(dst[key], key)
        for id_value, digest in dst_by_id.items():
            if id_value not in src_by_id:
                raise DeltaBlocked("Target-only business ID exists: " + key)
            if src_by_id[id_value] != digest:
                raise DeltaBlocked("Same business ID has conflicting content: " + key)
        missing = set(src_by_id).difference(dst_by_id)
        deltas[key] = len(missing)
        if key == "monitoringKlaim":
            added_claim_ids = missing
    if source_version == target_version and any(deltas.values()):
        raise DeltaBlocked("State version unchanged despite unreplicated records")
    return {
        "source_version": source_version,
        "target_version": target_version,
        "source_state_keys": len(src),
        "unchanged_state_keys": len(unchanged),
        "source_entries": {key: len(src[key]) for key in DELTA_KEYS},
        "target_entries": {key: len(dst[key]) for key in DELTA_KEYS},
        "source_only_entries": deltas,
        "target_only_entries": {key: 0 for key in DELTA_KEYS},
    }, added_claim_ids


def validate_attachment_path(value: object) -> None:
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise DeltaBlocked("Invalid storage object path")
    if (value.startswith("/") or "\\" in value or any(p in (".", "..", "") for p in value.split("/"))
        or any(ord(c) < 32 for c in value)):
        raise DeltaBlocked("Storage object path fails safety checks")


def check_attachments(source: object, target: object, source_state: object,
                      target_state: object, new_claim_ids: set[str]) -> dict:
    if not isinstance(source, list) or not isinstance(target, list):
        raise DeltaBlocked("Attachment inventories must be JSON arrays")
    _, src_state = validate_state(source_state)
    _, dst_state = validate_state(target_state)
    all_claim_ids = set(id_records(src_state["monitoringKlaim"], "monitoringKlaim"))
    target_claim_ids = set(id_records(dst_state["monitoringKlaim"], "monitoringKlaim"))
    result = {}
    unique_names = set()
    unique_paths = set()
    owners = set()
    with_blob_sha = 0
    total_bytes = 0
    for a in source:
        if not isinstance(a, dict):
            raise DeltaBlocked("Malformed source attachment")
        aid = safe_id(a.get("id"))
        owner = safe_id(a.get("owner_id"))
        filename = a.get("file_name")
        if a.get("owner_type") != EXPECTED_OWNER or owner not in all_claim_ids:
            raise DeltaBlocked("Attachment owner does not belong to a claim")
        if not isinstance(filename, str) or not filename:
            raise DeltaBlocked("Missing attachment filename")
        if a.get("mime_type") not in MIME_ALLOWLIST:
            raise DeltaBlocked("Unexpected attachment MIME type")
        size = a.get("size_bytes")
        if type(size) is not int or size <= 0 or size > MAX_FILE_BYTES:
            raise DeltaBlocked("Invalid source attachment size")
        path = a.get("storage_path")
        validate_attachment_path(path)
        owner_name = (owner, filename)
        if aid in result or owner_name in unique_names or path in unique_paths:
            raise DeltaBlocked("Duplicate attachment ID, filename or object path")
        unique_names.add(owner_name)
        unique_paths.add(path)
        owners.add(owner)
        total_bytes += size
        blob_hash = a.get("blob_sha256")
        if blob_hash is not None:
            if not isinstance(blob_hash, str) or len(blob_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in blob_hash):
                raise DeltaBlocked("Invalid source object SHA256 proof")
            with_blob_sha += 1
        if "object_size_bytes" in a and a["object_size_bytes"] != size:
            raise DeltaBlocked("Storage object size differs from attachment metadata")
        result[aid] = a

    dst_by_id = {}
    for a in target:
        if not isinstance(a, dict):
            raise DeltaBlocked("Malformed target attachment")
        aid = safe_id(a.get("id"))
        if aid in dst_by_id:
            raise DeltaBlocked("Duplicate target attachment ID")
        dst_by_id[aid] = a
    missing = 0
    target_only = 0
    for aid, dest in dst_by_id.items():
        if aid not in result:
            target_only += 1
        else:
            src = result[aid]
            for field in ("owner_type", "owner_id", "file_name", "mime_type", "size_bytes", "storage_path"):
                if src.get(field) != dest.get(field):
                    raise DeltaBlocked("Existing attachment ID contains incompatible metadata")
            src_sha = src.get("blob_sha256")
            dest_sha = dest.get("blob_sha256")
            if src_sha is not None and dest_sha is not None and src_sha.lower() != dest_sha.lower():
                raise DeltaBlocked("Existing Storage object has conflicting byte hash")
    if target_only:
        raise DeltaBlocked("Target-only attachment IDs require conflict review")
    for aid, a in result.items():
        if aid not in dst_by_id:
            missing += 1
            if a["owner_id"] not in (new_claim_ids | target_claim_ids):
                raise DeltaBlocked("New attachment references unrecognized target claim")
    return {
        "source_attachments": len(source),
        "target_attachments": len(target),
        "missing_attachment_metadata": missing,
        "source_attachment_owners": len(owners),
        "total_source_bytes": total_bytes,
        "source_objects_with_byte_sha256": with_blob_sha,
        "source_object_bytes_all_attested": with_blob_sha == len(source),
    }


def plan(source_state: object, target_state: object,
         source_attachments: object, target_attachments: object) -> dict:
    state_info, missing_claim_ids = state_delta(source_state, target_state)
    attachment_info = check_attachments(
        source_attachments, target_attachments, source_state, target_state,
        missing_claim_ids)
    return {
        "mode": "READ_ONLY_PLAN",
        **state_info,
        **attachment_info,
        "ready_for_cutover": False,
        "remaining_gates": [
            "full PostgreSQL and Storage restore demonstrated in isolated environment",
            "external write freeze and consistent source snapshot approved",
            "Storage object byte hashes verified and private bucket access E2E",
            "transactional state version/CAS, attachment metadata, audit and realtime signal migration E2E",
            "approved rollback and owner-authorized change",
        ],
    }


def read_snapshot(path_str: str) -> object:
    path = Path(path_str)
    if not path.is_file() or path.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise DeltaBlocked("Missing or oversized private input file")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError):
        raise DeltaBlocked("Invalid JSON input file") from None


def main() -> int:
    parser = argparse.ArgumentParser(description="CSB Klarin secure READ-ONLY delta planner")
    parser.add_argument("--source-state", required=True)
    parser.add_argument("--target-state", required=True)
    parser.add_argument("--source-attachments", required=True)
    parser.add_argument("--target-attachments", required=True)
    args = parser.parse_args()
    try:
        summary = plan(
            read_snapshot(args.source_state),
            read_snapshot(args.target_state),
            read_snapshot(args.source_attachments),
            read_snapshot(args.target_attachments),
        )
        print(json.dumps(summary, sort_keys=True, indent=2))
        return 0
    except (DeltaBlocked, OSError):
        print("NO-GO: private snapshot safety, identity, ownership or data integrity check failed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
