# GPP Stock private files — two BASE operator-only transfer gate (NO-GO until restored)

Last live-read-only census: 22 Nov 2026. This document **does not** authorize copying production files, changing app state, or decommissioning projects.

## Exact scope — do not mix tenant buckets

| Stage | Supabase project | Workspace/schema | Private bucket |
|---|---|---|---|
| Original | `aupbqpdxiqulxcxeewri` (gpp-stock) | `public`, `gpp_pusat` | `gpp-klarin-attachments` |
| Destination | `numlkqppirrxfwdhazja` (bbm-klarin) | `gpp_stock`, `gpp_pusat` | `gpro-gpp-private-attachments` |

The GPP destination private bucket **already exists** (50 MiB, `public=false`), with **0 Storage objects** at last live audit. Do not place GPP files in BBM `klarin-private-attachments` or CSB `gpro-csb-private-attachments`.

Legacy GPP Stock contains **2 original objects**, 1 PDF + 1 XLSX, total **4,231,865 bytes**, and 2 matching attachment rows with no missing/orphan metadata. Both are owned by workspace `gpp_pusat`; **GPP Cabang has no source attachment** in this inventory. GPP Pusat state version **6 source / 4 target**. GPP Cabang is **version 1 / 1**, with matching SHA-256 of state. These are **historical unfrozen values**, not approved command arguments.

## Gate A — owner-authorized recovery and region checks

Before any `--write-private-manifest` or `--apply`:

1. Privately create full PostgreSQL **and all actual Storage byte** backups of all seven Supabase projects, including Auth, permissions, RLS, application tables, and bucket contents. Include physical file SHA-256. Backup must be external to the projects scheduled for retirement.
2. Prove successful isolated restoration of each backup, verify row/byte hashes, login and application read/write against restored data. Record the signed restore evidence and tested rollback privately; do not create a paid Supabase project without owner approval.
3. Obtain owner/controller approval for the CSB Singapore-to-Mumbai data movement separately. Do not infer data-residency approval from SQL success.
4. Obtain an **external application-write freeze** and fresh source and target GPP Pusat version/hash, plus the GPP Cabang frozen version/hash. Database read-only snapshots do not freeze applications. Ensure GPP Cabang remains untouched.
5. Verify source metadata/Storage objects and their bytes again; inventory may have changed. Sign the `expected-objects` and `expected-total-bytes` approval using frozen source, not the historical 2 and 4,231,865 if drift is detected.

## Gate B — source manifest (no live writes)

Run `python3 ops/scripts/gpp_stock_private_manifest_guarded.py` with no arguments for a no-network dry-run. In an approved private operator environment only, provide a pinned source owner PostgreSQL DSN via `GPRO_GPP_STOCK_SOURCE_DSN`, and a separate server-only Storage credential via `GPRO_GPP_STOCK_SOURCE_STORAGE_SERVICE_KEY`. Never enter DSNs, tokens, real object paths, customer IDs, private JSON manifests or file bytes in GitHub, chat, issue comments or CI.

The generator takes these flags:

```text
--write-private-manifest
--manifest-out /secure/gpp-private-manifest.json
--approved-change-ref <signed-ticket-ref>
--verified-restore-ref <actual-isolated-restore-proof>
--frozen-inventory-ref <actual-write-freeze-proof>
--confirm-frozen-writes
--source-version <fresh-gpp-pusat-version>
--source-state-sha256 <fresh-source-gpp-pusat-hash>
--cabang-version <fresh-gpp-cabang-version>
--cabang-state-sha256 <fresh-gpp-cabang-hash>
--expected-objects <fresh-object-count>
--expected-total-bytes <fresh-byte-total>
```

The manifest generator reads only legacy PG in a repeatable-read read-only snapshot, confirms the **two workspaces**, exact object metadata and file sizes, authenticates original Storage GET, computes actual byte SHA-256, and exclusively creates a local protected 0600 manifest in a 0700 directory. This manifest is **not** a replacement for an independently restored physical backup.

## Gate C — physical stage (only after Gate A/B)

After a complete private manifest and two separate encrypted owner-only local source/target directories exist, use `python3 ops/scripts/gpp_stock_storage_stage_guarded.py` with `--manifest`, fresh inventory counts, version digests, operator proof flags, and `--apply`, also including `--source-root`, `--target-root`, `--target-state-sha256`. Provide **distinct** protected credentials via `GPRO_GPP_STOCK_SOURCE_STORAGE_SERVICE_KEY` and `GPRO_GPP_STOCK_TARGET_STORAGE_SERVICE_KEY`. The stage helper does not directly verify signed restore tickets: operator must independently validate Gate A.

Stage behavior: source authenticated GET, SHA-256 before upload, target authenticated GET, **POST with `x-upsert=false` only if missing**, authenticated target GET readback, second SHA-256 and independent protected-local file audit. It never deletes originals or overwrites source/target files. Partial uploads remain after a failure and require operator review, not automatic deletion.

**Important:** The current stage helper verifies content hashes and approved inventory but does not itself re-query GPP live state/ACL. Before `--apply`, the operator must independently rerun the frozen source/target SQL checkpoints for both Pusat and Cabang and confirm the private target bucket. Do not treat a supplied `--target-state-sha256` flag as proof of that live comparison.

## Gate D — NOT implemented by the byte-stage tool

After physically verified staging, do a **separate** approved, serializable/optimistic-CAS metadata and GPP Pusat claim state reconciliation with exact frozen source/target hashes and RLS. Preserve GPP Cabang version 1 and records verbatim. Do not copy stale sessions, overwrite a user's rows, or copy Pusat claims into Cabang. Test real app login, upload, download, delete, tenant-positive/tenant-negative permissions, audit trail, journaling and rollback.

Current status: no independent restored full backup, no actual GPP private byte transfer, no metadata CAS, and no application E2E proof. **NO-GO for production cutover and deletion of any of the five legacy Supabase projects.**
