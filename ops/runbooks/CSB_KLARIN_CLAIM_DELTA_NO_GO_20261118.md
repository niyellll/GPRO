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
