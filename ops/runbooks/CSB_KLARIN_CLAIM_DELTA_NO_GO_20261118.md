# CSB Klarin — claim state + private attachment delta (NO-GO)
**Live read-only investigation: 18 November 2026.** No target mutations, no file moves, no account resets, no service keys exposed.

## Source/target
- Legacy source `krwoiucqfcijmihnrlem`, `public` / bucket `klarin-private-attachments`.
- Target BASE `numlkqppirrxfwdhazja`, tenant `csb_klarin` / bucket `gpro-csb-private-attachments`.
- Source app state `default`: **version 40**, updated 2026-11-18, **21 JSON top-level keys**.
- Target app state `default`: **version 38**, last updated 2026-11-07, **21 JSON top-level keys**.
- Live SHA-256 per-state-key checks show **18 keys identical and 3 keys different**:
  - `monitoringKlaim`: 4 source records / 0 target records.
  - `uploadBatches`: 2 source entries / 1 target entry.
  - `auditLogs`: 39 source entries / 37 target entries.
- Read-only element-level JSON fingerprints: the **existing target array entries form subsets** of their respective source arrays, with source-only differences of **4 claims, 1 upload batch, 2 audit logs**, **0 target-only entries** in the examined snapshot. This is *not* a frozen or cross-project atomic snapshot and can change while users work.
- Source `klarin_stock_claim_attachments`: six metadata records, 2,918,989 bytes total, 6/6 matching physical legacy Storage objects, no base64 payload. Target tenant metadata had 0 matching records in prior inventory, target CSB private Storage bucket remains empty. File owner references and checksums must be verified before copying.

## Executed verification
- SQL source and target fingerprints in `ops/sql/csb_klarin_state_source_READ_ONLY.sql` and `ops/sql/csb_klarin_state_target_READ_ONLY.sql` **executed successfully** against the live source and target.
- Only aggregate counts, version, JSON key identity and SHA-256 are recorded here; **no raw claim content, user details, sessions, file bytes or passwords were committed to this public repository**.
- No cloud upload, Storage copy, write operation or full backup/restore was executed.

## Correctness requirements for a future guarded delta
1. **STOP** until PostgreSQL + Storage full source and target backups have been restored in isolated test environment. Maintain rollback and check BLOB integrity (SHA-256 of actual file bytes).
2. Freeze or otherwise transactionally checkpoint **all CSB legacy writes**, including claim edits, uploads, state updates and attachments, then refresh live fingerprints; do not rely on the historical version 40/38.
3. Determine whether the six source attachment owners belong to the four claims, using stable `owner_type`, `owner_id`, object paths and ownership metadata, not filenames alone.
4. Copy the six private objects to the **CSB dedicated target bucket**, with access restrictions, content type, byte size and checksums preserved. Never expose service-role keys in browser or logs. Idempotently map paths and preserve owner IDs.
5. Copy the corresponding attachment metadata only after target object reads by authorized CSB session pass; test rejection of reads by GPP and BBM.
6. Merge **only unmatched entries**, using stable business IDs and canonical content comparison; require explicit conflict review if an ID exists with a different content hash. Do not overwrite target state wholesale and never delete a target-only record.
7. Preserve app-state optimistic concurrency: compare expected `version` within a transaction and abort if it changes. Keep audit logging append-only, batch IDs idempotent, and counter/signaling semantics reviewed; do not silently set a lower version.
8. E2E test claim create/edit/cancel, upload, download, preview PDF, inventory/retur permissions and role denial with isolated fixtures.
9. Verify all 21 source/target app-state keys at a **consistent final checkpoint**, plus row counts, per-item hashes, metadata and physical objects; confirm no pending change or duplicate.
10. Only after remaining all-app migration/restore tests pass may production be cut over. Five old projects still require explicit separate approval before deletion.

**Status: NO-GO.** There are **7 source-only app-state array entries** and **6 legacy CSB attachment objects** requiring owner-aware and version-safe migration. Source remains active.


## Verified owner linkage and tenant privacy checks (live, 18 Nov)
The schema inventory and the reviewed read-only SQL files established:
- Source attachment metadata **6/6 with unique IDs and distinct Storage object paths**, **all 6 owner_type=`klaim`**, linked to **one** source claim ID contained in the four missing `monitoringKlaim` records.
- All six source objects match metadata path AND size; total **2,918,989 bytes**. Inline `data_base64` is empty on **all six**. Contents are **four PDFs and two XLSX files**.
- Target `csb_klarin.klarin_stock_claim_attachments` has 0 rows and its dedicated `gpro-csb-private-attachments` bucket has 0 objects. Bucket is `public=false`, table has RLS enabled, and neither `anon` nor `authenticated` has SELECT grants; trusted `service_role` retains server-only CRUD.
- This proves **metadata and object-size correspondence only**, not SHA-256 of actual Storage bytes. No authenticated file download, upload, signed URL or object copy was attempted.
- Independently verified that **all three JSON arrays use stable nonempty unique IDs**: source 4/2/39 and target 0/1/37 for claim/batch/audit. No duplicate ID in the examined snapshot.

**Executed SQL (both queries passed):**
- `ops/sql/csb_klarin_claim_attachment_source_READ_ONLY.sql`
- `ops/sql/csb_klarin_claim_attachment_target_READ_ONLY.sql`

## Privacy-safe snapshot delta planner
- `ops/scripts/csb_klarin_claim_delta_plan.py` is an **offline, local JSON analysis tool only**. There is **no `--apply` mode, network access, database write or Storage action**.
- It receives **four private JSON files**: `--source-state`, `--target-state`, `--source-attachments`, `--target-attachments`. Real files must be exported solely to a trusted encrypted operator environment after the formal source freeze; never share their contents via GitHub or chat.
- State file envelope: `{"version": <integer>, "state": <raw JSON state>}`. Do NOT generate the state envelope from a non-transactional or partially copied snapshot. On source this comes from `public.klarin_stock_claim_app_state` for `workspace_key='default'`; on target from `csb_klarin.klarin_stock_claim_app_state` (same key).
- Attachment arrays need these source columns: `id`, `owner_type`, `owner_id`, `file_name`, `mime_type`, `size_bytes`, `storage_path`. Source export can also include trusted `object_size_bytes` from `storage.objects` metadata and independently downloaded `blob_sha256` for the actual bytes. Target attachment array may be `[]` if verified empty. DO NOT include `data_base64` or secrets in the input.
- Output contains **only aggregated counts**, no raw customer fields, owner identifiers, file paths, filenames or session tokens. Unexpected state-key drift, duplicate IDs, changed contents with the same ID, target-only entries, owner mismatches, unsafe paths, unsupported MIME types, mismatched byte sizes, or broken hash attestations produce NO-GO.
- Current live counts are **not a consistent write-frozen checkpoint**. This tool has not been executed with raw private live snapshots, so no live snapshot plan result is asserted.
- Its 13 synthetic offline tests passed together with the nine GPP RK tests in GitHub Actions run `44345849110` (**22/22 PASS**). That proves code/fixture contracts only, not real cloud transfer.
- The explicit `ready_for_cutover=false` output is intentionally permanent: even fully validated JSON/Storage manifests do not prove the remaining real backup, authentication and E2E gates.

## Security advisor context
The Supabase Security Advisors were read-only-checked on both BASEs. Finance showed **10 INFO-level** `rls_enabled_no_policy` notices for `public` tables, Klarin showed **6 INFO-level** notices for `public` tables; there were no other reported lints in those checks. These notices alone are NOT evidence of public read access—RLS without any policy is typically deny-by-default. Keep existing intentional fail-closed grants. Remediation guidance: https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy


## Phase-zero original byte SHA-256 check (offline; no upload, no live write)
The CSV/SQL metadata size checks above are insufficient to prove that the **actual bytes** of a PDF/XLSX are intact. Added `ops/scripts/csb_klarin_storage_byte_audit.py` for this gap, using only Python standard-library modules and no network/DB operations. The operator should keep raw file bytes and private manifest in an **encrypted, access-restricted temporary workspace**, never commit them to GitHub or upload them to chat.

Secure private manifest is a JSON array of original attachment metadata, one entry per unique `id` with `owner_type`, `owner_id`, `file_name`, `mime_type`, `size_bytes`, `storage_path`. Optional `target_storage_path` is allowed only when an approved target mapping differs; optional `expected_sha256` should be independently obtained from authenticated source byte download. Do not copy `data_base64`, credentials, session tokens or business fields into the manifest.

1. After an authorized, audited **external source write freeze**, requery **exact attachment row count and total bytes**, including object path and size metadata; confirm the same six source claim IDs and state version at the checkpoint.
2. Export/download **actual private object bytes** using an approved authenticated Supabase Storage CLI/S3 client or authorized Dashboard flow; preserve relative object paths rooted in a local `source/` directory. Do not treat `storage.objects` metadata rows as the file payload.
3. Run source-only verification (use current totals below **only if freshly reconfirmed after freeze**):
   ```bash
   python3 ops/scripts/csb_klarin_storage_byte_audit.py \
     --manifest /secure/csb/attachments-manifest.json \
     --source-root /secure/csb/source \
     --expected-objects 6 \
     --expected-total-bytes 2918989
   ```
   This computes SHA-256 of each source object, checks every byte size, validates path containment, rejects symlinks, prevents duplicate IDs, and counts independently supplied expected hash proofs. It **does not** claim the target was checked.
4. Following a separately authorized Storage transfer (NOT performed in this PR), export the actual **target** private objects into an independent local `target/` directory, preserve the approved object mapping, and repeat with `--target-root /secure/csb/target`. Source and target roots **must differ**. File byte hashes must match exactly; any missing/modified file is NO-GO.
5. The report exposes aggregate counts only, **never raw object keys, file names, customer/claim IDs, or full file SHA hashes**. `source_expected_sha256_proofs_verified` counts independently supplied trusted source checksums; if absent it reports **0**, not false provenance.
6. **The utility always reports `ready_for_cutover=false`.** Full DB+Storage restoration, app-state CAS, session/role permissions, metadata linking, signed change record, final cross-project consistency and actual cloud E2E remain independently required. An offline byte match alone does not authorize deployment, database writes, or deletion.

GitHub Actions tests are **synthetic, offline, no customer files or credentials**. Supabase source/target Storage objects have **NOT** yet been physically downloaded, copied or byte-verified.
