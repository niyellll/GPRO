#!/usr/bin/env python3
"""Create a private manifest of real source CSB Klarin file-byte SHA-256 proofs.

Operator-only tool. DEFAULT: no network or I/O except argument parsing.
Approved --write-private-manifest reads ONLY the pinned legacy PostgreSQL source
and authenticates to its private Storage bucket; no live DB or Storage writes.
Writes source attachment identities and hashes ONLY on a locally protected
operator computer (0700 directory, exclusive 0600 file), NEVER GitHub/chat.

Requires a real isolated full PostgreSQL + physical Storage restore drill,
documented source write freeze, and fresh source state SHA-256/version.
Follow with csb_klarin_storage_stage_guarded.py and state_transfer_guarded.py.
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

from csb_klarin_state_transfer_guarded import (
    SOURCE_REF, SOURCE_BUCKET, require_operator_url,
)
from csb_klarin_storage_byte_audit import (
    ByteAuditBlocked, MAX_FILE_SIZE, MAX_MANIFEST_SIZE, normalized_storage_path,
    private_manifest, verified_local_root,
)
from csb_klarin_storage_stage_guarded import (
    KEY_PATTERN, SOURCE_SECRET, StorageHttp, storage_url,
)

SHA_PATTERN = re.compile(r"[0-9a-fA-F]{64}\Z")
SOURCE_DSN_ENV = "GPRO_CSB_KLARIN_SOURCE_DSN"
COLUMNS = (
    "id","owner_type","owner_id","file_name","mime_type",
    "size_bytes","storage_path","data_base64"
)


class ManifestBlocked(ValueError):
    pass


def require_gates(args) -> None:
    if not args.write_private_manifest:
        return
    if not (
        args.confirm_frozen_writes
        and args.approved_change_ref.strip()
        and args.verified_restore_ref.strip()
        and args.frozen_inventory_ref.strip()
        and args.manifest_out.strip()
        and args.source_version >= 1
        and args.expected_objects >= 1
        and args.expected_total_bytes >= 1
        and SHA_PATTERN.fullmatch(args.source_state_sha256)
    ):
        raise ManifestBlocked("Fresh source snapshot, restore and external write freeze are required")


def check_snapshot(cursor,args):
    cursor.execute("""
        SELECT version,encode(sha256(convert_to(state::text,'UTF8')),'hex') AS hash
          FROM public.klarin_stock_claim_app_state WHERE workspace_key='default'
    """)
    row=cursor.fetchone()
    if (row is None or row["version"]!=args.source_version or
        row["hash"] != args.source_state_sha256.lower()):
        raise ManifestBlocked("Original claim state no longer matches frozen checkpoint")
    cursor.execute("SELECT version FROM public.klarin_realtime_signal WHERE workspace_key='default'")
    signal=cursor.fetchone()
    if signal is None or signal["version"] != args.source_version:
        raise ManifestBlocked("Realtime source signal differs from frozen state version")


def validate_inventory(rows, storage_inventory, count, total):
    if len(rows)!=count or len(storage_inventory)!=count:
        raise ManifestBlocked("Source attachment/object count changed")
    by_path={}
    metadata_total=0
    for row in rows:
        if row["owner_type"]!="klaim" or row["data_base64"] not in ("",None):
            raise ManifestBlocked("Source attachment ownership or encoding changed")
        size=row["size_bytes"]
        if type(size) is not int or size<=0 or size>MAX_FILE_SIZE:
            raise ManifestBlocked("Source attachment size outside approved bounds")
        path=normalized_storage_path(row["storage_path"])
        if path in by_path:
            raise ManifestBlocked("Duplicate source Storage path")
        by_path[path]=size
        metadata_total+=size
    objects={entry["name"]:entry["size"] for entry in storage_inventory}
    if len(objects)!=len(storage_inventory) or objects!=by_path or metadata_total!=total:
        raise ManifestBlocked("PostgreSQL attachment and physical Storage metadata mismatch")
    return by_path


def build_private_manifest(rows, inventory, expected_objects, expected_bytes, key, transport):
    """Compute genuine SHA-256 from the original authenticated private object bytes."""
    validate_inventory(rows, inventory, expected_objects, expected_bytes)
    entries=[]
    for row in rows:
        path=normalized_storage_path(row["storage_path"])
        limit=row["size_bytes"]
        private_url=storage_url(SOURCE_REF,SOURCE_BUCKET,path,private_read=True)
        raw=transport.request("GET",private_url,key,maximum_bytes=limit)
        if raw is None or len(raw)!=limit:
            raise ManifestBlocked("Private original object missing or length differs from database")
        entry={k:row[k] for k in COLUMNS if k!="data_base64"}
        entry["expected_sha256"]=hashlib.sha256(raw).hexdigest()
        entries.append(entry)
    return entries


def save_manifest_exclusive(path: Path,entries):
    """Only operator local filesystem; NEVER upload result to GitHub/chat."""
    if path.is_symlink() or not path.parent.is_dir() or path.parent.is_symlink():
        raise ManifestBlocked("Private output path must have a preexisting secure parent")
    parent=verified_local_root(path.parent)
    if os.name=="posix" and parent.stat().st_mode & 0o077:
        raise ManifestBlocked("Private manifest directory must be chmod 700")
    output=json.dumps(entries,ensure_ascii=False,sort_keys=True,indent=2).encode("utf-8")
    if len(output)>MAX_MANIFEST_SIZE:
        raise ManifestBlocked("Manifest size exceeds safe limit")
    flags=os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd=os.open(path,flags,0o600)
        with os.fdopen(fd,"wb") as stream:
            stream.write(output)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError:
        raise ManifestBlocked("Private manifest already exists or cannot be saved") from None
    # Revalidate actual on-disk data without printing any ID, path or customer field.
    valid=private_manifest(path)
    if len(valid)!=len(entries):
        raise ManifestBlocked("Output manifest validation mismatch")


def parser():
    p=argparse.ArgumentParser(description="Source-only private CSB manifest generator; no-network by default")
    p.add_argument("--write-private-manifest",action="store_true")
    p.add_argument("--manifest-out",default="")
    p.add_argument("--approved-change-ref",default="")
    p.add_argument("--verified-restore-ref",default="")
    p.add_argument("--frozen-inventory-ref",default="")
    p.add_argument("--confirm-frozen-writes",action="store_true")
    p.add_argument("--source-version",type=int,default=0)
    p.add_argument("--source-state-sha256",default="")
    p.add_argument("--expected-objects",type=int,default=0)
    p.add_argument("--expected-total-bytes",type=int,default=0)
    return p


def main():
    args=parser().parse_args()
    try:
        require_gates(args)
        if not args.write_private_manifest:
            print(json.dumps({
                "mode":"NO_NETWORK_DRY_RUN",
                "requires":"approved restore + frozen SQL source checkpoint + protected DSN/key",
                "write_operations":0,"ready_for_cutover":False,
            },sort_keys=True))
            return 0
        source_dsn=os.environ.get(SOURCE_DSN_ENV,"")
        require_operator_url(source_dsn,SOURCE_REF)
        key=os.environ.get(SOURCE_SECRET,"")
        if not KEY_PATTERN.fullmatch(key):
            raise ManifestBlocked("Authorized source private Storage key unavailable")
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError:
            raise ManifestBlocked("psycopg3 required in private operator environment") from None
        with psycopg.connect(source_dsn,connect_timeout=12,sslmode="require",
                             autocommit=True,row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute("BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                check_snapshot(cursor,args)
                cursor.execute(
                    "SELECT id::text AS id,"+",".join(COLUMNS[1:])+
                    " FROM public.klarin_stock_claim_attachments ORDER BY id")
                rows=cursor.fetchall()
                cursor.execute("""
                    SELECT name,COALESCE((metadata->>'size')::bigint,-1) AS size
                    FROM storage.objects WHERE bucket_id=%s
                """,(SOURCE_BUCKET,))
                inventory=cursor.fetchall()
                manifest=build_private_manifest(rows,inventory,args.expected_objects,
                                                args.expected_total_bytes,key,StorageHttp())
                cursor.execute("ROLLBACK")
        save_manifest_exclusive(Path(args.manifest_out),manifest)
        print(json.dumps({
            "mode":"OPERATOR_PRIVATE_MANIFEST_CREATED",
            "objects":len(manifest),"bytes":args.expected_total_bytes,
            "source_genuine_byte_sha256_verified":len(manifest),
            "postgresql_writes":0,"storage_writes":0,
            "ready_for_cutover":False,
        },sort_keys=True))
        return 0
    except Exception:
        # psycopg and HTTPS failures may include connection details in exception
        # strings. Suppress every raw exception before it reaches operator logs.
        print("NO-GO: source restore, frozen inventory, private bytes, or local manifest validation failed",
              file=sys.stderr)
        return 2


if __name__=="__main__":
    raise SystemExit(main())
