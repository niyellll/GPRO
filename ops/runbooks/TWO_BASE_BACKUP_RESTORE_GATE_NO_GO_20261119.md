# Two-BASE — offline backup and restore gate (NO-GO)
**Last direct read-only inventory: 19 November 2026, Asia/Jakarta.**
**Applies to all 7 currently active Supabase projects; this document authorizes NO write or deletion.**

## Why this remains a release blocker
Official Supabase guidance distinguishes **database dumps** from **physical Storage objects**: the PostgreSQL `storage.objects` rows contain file metadata, NOT the underlying PDF/XLSX and other object bytes. An object inside an app's "backup" bucket must not be assumed to be a restorable DB backup without examining its format and completing a real restore drill.

Direct catalog-only checks on the two destination BASEs:
- `bbm-finance` `fdhqidjltlihzdcbqfrd`: `finance-private-backups` contains **66 objects**, largest just **202 bytes**. These tiny markers **cannot be accepted as proof** of a full PostgreSQL database export/restore.
- `bbm-klarin` `numlkqppirrxfwdhazja`: `klarin-private-backups` contains **67 objects**, largest about **20.7 MB**; contents and actual successful restore **not verified**. Their existence alone is NOT a release gate.
- Finance three and Klarin two dedicated tenant login roles currently have no password in Postgres catalog: **3 + 2 = 5 unverified tenant DB logins**. Do NOT publish credentials or enable Preview flags to circumvent authentication.

## Required operator-owned artifacts (kept private, never committed)
For **each of seven active projects** (two BASEs plus five legacy sources), prepare:
1. Project-ref-verified, full **roles + schema + data** PostgreSQL export using the current [Supabase database migration guide](https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore). Use a reviewed CLI version and Docker. If using `supabase db dump`, the guide describes `--role-only`, a schema export, and a `--use-copy --data-only` export. Do NOT assume an app-generated JSON marker is the database dump.
2. A **separate actual Storage-object export**, including all needed private buckets, the complete original bytes, path map, MIME/size, and per-object SHA-256. Source PDF/XLSX and other customer files must never be put into a public repo, chat or CI artifact. [Official Storage documentation](https://supabase.com/docs/guides/storage/management/download-objects) explains the separate object transfer.
3. A sealed backup manifest with project ref, snapshot time/time zone, source application write-freeze evidence, database Postgres major version, schema inventory, normalized table row-counts and hashes, object counts/bytes/byte-digests, and backup artifact SHA-256.
4. Independently reviewed encrypted storage location, retention policy, named operator, authorization record and secure secret-management workflow. Never pass connection strings through GitHub comments, application bundles or unredacted command logs.

## Restore drill: use an EXISTING isolated throwaway environment
- Do **not** restore directly into either destination BASE, an active legacy project, or production Preview. Do not create a new paid Supabase project, branch, plan upgrade or billable resource.
- Have an authorized operator provide a pre-existing, isolated PostgreSQL + Storage test environment with enough capacity; PostgreSQL and extension versions must be checked before import.
- Verify backup tar/SQL manifests are complete and their SHA-256 matches the sealed copy. Inspect for internal Supabase schema exclusions and reserved roles. Do not use a destructive `DROP DATABASE` or `--clean` flag against live projects.
- Restore roles/schema/data with CLI/psql according to the approved procedure, logging exit codes, table/constraint/index counts, row counts, total amounts and selected deterministic SHA-256 fingerprints. **Success means executing an actual restore**, not a static file inspection.
- Rehydrate object bytes separately in isolated Storage, then authenticate to read random and high-risk business attachments, comparing each byte SHA-256 with source manifest, object count, byte totals and permissions.
- Negative security tests must prove a CSB account cannot access GPP's private Storage or finance schema, and an anonymous browser key cannot read tenant metadata. Exercise login/refresh, app read/write, PDF/XLSX download, upload, claims, journals and lock periods.
- Record measured RTO (time to restore), RPO (acceptable loss window), the recovered snapshot marker, failed jobs, rollback triggers and explicit reviewer sign-off. Fail/no-go if any component or object is missing, or snapshots are not consistent.

## Guarded cutover depends on a PASS restore drill
Sequence: encrypted full source+target exports → actual isolated restore PASS → tenant identity and write-authority E2E PASS → successful Preview build/health without paid quota bypass → approved live-write freeze → final source/target count+hash delta → per-business-ID conflict-safe import and storage-byte copy → end-to-end app QA → **separate owner approval** before cutover. Keep all legacy projects active until rollback window expires and deletion is explicitly and separately approved.

**Currently STOP / NO-GO.** These gates cannot be greened by source-code tests alone. Neither the 37/37 GitHub Actions offline safety tests nor a private bucket's object count proves successful backup restoration.

**Reference evidence:** [GPRO live audit](https://github.com/niyellll/GPRO/blob/audit/two-base-live-reconciliation-20261118/docs/two-base-live-audit-20261118.md) and [CSB claim byte check](https://github.com/niyellll/GPRO/blob/audit/two-base-live-reconciliation-20261118/ops/runbooks/CSB_KLARIN_CLAIM_DELTA_NO_GO_20261118.md).
