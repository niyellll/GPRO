# CSB Klarin — real private Storage object staging (operator-only; NO-GO live)

**Status, 19 Nov 2026:** This runbook and script are published for review; **NO source-to-target physical object transfer has been run**, no Supabase credential exists in GitHub Actions or this repository, and no backup/restore drill has been verified. Six source objects (2,918,989 bytes) remain in legacy private bucket; dedicated target CSB bucket has zero objects.

## Pinning and exact scope

- Source: `krwoiucqfcijmihnrlem`, private Storage bucket **`klarin-private-attachments`**.
- Target: `numlkqppirrxfwdhazja`, private Storage bucket **`gpro-csb-private-attachments`**. Do not use the target's *other* `klarin-private-attachments` bucket belonging to BBM.
- Data: six original CSB claim attachments, presently 4 PDFs and 2 XLSX, totaling 2,918,989 bytes at the latest **unfrozen** snapshot. File identities and paths stay private. Source records remain intact.
- `ops/scripts/csb_klarin_storage_stage_guarded.py` uses Supabase's authenticated private GET `/storage/v1/object/authenticated/{bucket}/{path}` and standard no-upsert POST `/storage/v1/object/{bucket}/{path}` through exact HTTPS project URLs. Source never receives POST and target never receives DELETE/PUT. Each object must match the independently recorded SHA-256, byte length, MIME, owner and path.
- **Never** add service keys or private manifests to GitHub, ChatGPT, Vercel browser environment, actions logs or tickets. All keys are server-only and per-project.

## Independent preflight required BEFORE --apply

1. A designated operator completes full encrypted PostgreSQL (all roles, schemas, data, auth dependencies) **and physical Storage** backups of **all seven** projects, performs and records a **successful isolated restore drill**, and verifies a working rollback. Database backups alone do not include actual Storage file bytes. See `TWO_BASE_BACKUP_RESTORE_GATE_NO_GO_20261119.md`.
2. Freeze all CSB Klarin claim writes and uploads at the source and destination, record a signed change identifier and the frozen source/target state version and `state::text` SHA256 from **both** `csb_klarin_*_locked_snapshot_READ_ONLY.sql` queries. These SQL names do not acquire a write lock on their own.
3. Securely prepare a **private manifest JSON array** with **exactly all six source** `klarin_stock_claim_attachments` rows, including `id`, `owner_type`, `owner_id`, `file_name`, `mime_type`, `size_bytes`, `storage_path` and the independently measured `expected_sha256` of the original **file bytes**, **not** a database row digest. No customer data, JWT, passwords or raw file contents are committed to GitHub.
4. Confirm `expected_objects=6` and `expected_total_bytes=2918989` from **fresh frozen inventory**. Do not blindly reuse these previous observations if new files appeared. Ensure the target dedicated CSB bucket is private and empty, or any existing objects correspond **byte-for-byte** to the manifest.
5. In the approved isolated operator environment, provision two **different server-only** authenticated Storage credentials via a protected secret mechanism into environment variables `GPRO_CSB_KLARIN_SOURCE_STORAGE_SERVICE_KEY` and `GPRO_CSB_KLARIN_TARGET_STORAGE_SERVICE_KEY`. Legacy service_role JWT keys may work when the REST gateway permits them; if modern keys are in use, test actual permissions using an approved private route. On 401/403 the script must fail; **never** fall back to public buckets or disable authentication.
6. Prepare two **separate encrypted, access-restricted** directories with owner-only permissions (on POSIX: `mkdir -m 700`). The script saves original and target readbacks without overwriting existing local files. These directory trees are NOT GitHub artifacts.

## Step 1: offline / no-network rehearsal

```bash
python3 ops/scripts/csb_klarin_storage_stage_guarded.py \
  --manifest /secure/csb-private-manifest.json \
  --expected-objects 6 \
  --expected-total-bytes 2918989
```

This requires no secrets; prints only an aggregate. The manifest must have complete metadata and six independently verified expected file SHA-256 values. **No network call and no write** is made.

## Step 2: authorized Storage transfer (only after backup restore and external freeze)

```bash
python3 ops/scripts/csb_klarin_storage_stage_guarded.py \
  --manifest /secure/csb-private-manifest.json \
  --expected-objects 6 \
  --expected-total-bytes 2918989 \
  --source-root /secure/CSB_original \
  --target-root /secure/CSB_target_readback \
  --apply \
  --approved-change-ref '<signed change identifier>' \
  --verified-restore-ref '<actual isolated restore evidence>' \
  --frozen-inventory-ref '<write-frozen count, bytes, state snapshot evidence>' \
  --confirm-frozen-writes \
  --source-state-sha256 '<fresh SHA256 of source state::text>' \
  --target-state-sha256 '<fresh SHA256 of target state::text>'
```

**No live --apply was run while preparing this PR.** Do not enter private key values in command arguments or transcript. Keys must come from a restricted process environment. The IDs in the command above are operator attestations, not remotely verified by this Storage tool; the separate guarded PostgreSQL transfer validates actual live snapshots.

On apply, the script:
- only GETs each original object privately and checks length and expected SHA256 *before* any upload;
- checks target's private object first; **reuses only exact hash matches**, rejects any other existing content, and never overwrites;
- uploads missing objects via standard Supabase POST with `x-upsert=false`, then GETs the actual bytes back privately;
- saves separate original/target local copies and runs `csb_klarin_storage_byte_audit.py` internally for SHA256 parity; outputs only object and byte counts, always `ready_for_cutover=false`.

**Important non-atomicity:** six separate Storage uploads cannot be a global atomic transaction across two Supabase projects. If later operations fail, already-staged private target objects remain. Do not auto-delete them. Resume only with unchanged approved snapshot/manifest and hash checks, or record a reviewed rollback.

## Step 3: PostgreSQL metadata + app-state CAS, then E2E

Following complete physical staging, execute `csb_klarin_state_transfer_guarded.py` **separately** from an authorized environment using its full `--apply` gate, exact frozen state checks, `--source-root` and `--target-root`, and independent user/tenant access sign-off. It will append missing claim metadata and update state version (e.g. 38→40) by optimistic compare-and-swap **only** if the live tenant snapshot has not changed. It is not part of this Storage tool.

Re-run source/target state, attachment metadata, and private bucket inventories. Verify all six customer file contents and MIME types with **authenticated CSB session**, and test denial for BBM/GPP/anonymous users, upload, edit, journal links, and rollback. Only after all seven-project backup/restore evidence, full site testing, and signed production cutover may the five legacy projects be considered for a separate retention/decommission decision.

## REST API supporting references
- https://supabase.com/docs/guides/storage/serving/downloads
- https://supabase.com/docs/guides/storage/uploads/standard-uploads
- https://supabase.com/docs/guides/storage/management/download-objects

**Decision now: NO-GO to cutover or delete legacy projects.**
