# GPP Finance Pusat — rekening koran V439 migration (NO-GO runbook)
**Prepared from source and target live catalog on 2026-11-18.**
This is a **reviewed execution plan, not an authorization to run production DDL/DML**.

## Verified evidence
- Source: Supabase `vmpurwykfzcmculnnjfw` (`public.rekening_koran_working_lines_v439`) has **47 rows, 47 distinct UUIDs**, dates 2026-10-01 through 2026-10-31. Source table has **22 columns**, a UUID PK, one compound bank/date/order index, no user triggers, and RLS disabled.
- A read-only SHA-256 query ran successfully in the live source: `ops/sql/gpp_rk_source_fingerprint_READ_ONLY.sql`. **Do not treat that hash as stable until writes are frozen.**
- Target: `fdhqidjltlihzdcbqfrd`, tenant `gpp_piutang`, does **not** have this table or V543 period metadata table. BBM `public` contains a DIFFERENT RK table, which must not receive any GPP data.
- Main GPP branch `gpro-two-base-migration-20261116` imports `lib/gproFinanceSqlRouterV2.mjs`. When preview routing is explicitly enabled, it lexically remaps qualified `public.<table>` identifiers to the allowlisted tenant schema and sets transaction-local `search_path`. This is useful but **not a substitute for DB authorization**, as its source documentation says.
- The SQL router is deliberately fail-closed on some literal schema references (e.g., `'public'`, `'public.table'`). Bank upload paths call runtime `CREATE TABLE`, `ALTER TABLE`, and `CREATE INDEX`; read-only tenant database roles cannot be assumed to execute DDL/DML. These call paths require static and cloud E2E verification prior to enabling routing.
- Bank routes expect a **25-column** target V439 table (including `matched_journal_no`, `matched_source`, `attachment_note`) and a separate V543 period metadata table. The source V439 table holds 22 columns; normalize/project the **same original 22 columns** when comparing content.
- Five LOGIN roles have no password (`rolpassword IS NULL`), therefore genuine database login and backend writes are unproved. NO-GO.

## Files staged in GPRO (not executed)
- `ops/sql/gpp_piutang_rekening_koran_v439_create_REVIEW_ONLY.sql` — target DDL + RLS + tenant SELECT policy + fail-closed preflight; creates 25-column RK and V543 metadata tables.
- `ops/sql/gpp_rk_source_fingerprint_READ_ONLY.sql` — deterministic SHA-256 over source's original 22 fields; already executed successfully on source.
- `ops/sql/gpp_rk_target_fingerprint_READ_ONLY.sql` — same SHA-256 projection of 22 original fields in target after approved transfer.

## Hard gates (no exceptions by default)
1. Obtain full backup of both BASEs and all five sources, with metadata and Storage object bytes. Successfully **restore** to an isolated preexisting test environment; document exact source transaction snapshot, checksum, RTO/RPO, operator, and rollback path. A JSON marker or Storage snapshot alone is not PostgreSQL restore.
2. Resolve free-tier Preview quota without purchasing or bypassing quotas. Route GPP Pusat and Cabang on the exact reviewed SHA and branch. Verify only Finance target project `fdhqidjltlihzdcbqfrd`; no production domain switch.
3. Prove authenticated read-only role connections, search_path, and **deny** access to all other tenants. Preserve separation for user/admin roles and Pusat/Cabang. Find a reviewed backend transaction-writer with audited authorization; **do not grant DML to read-only tenant roles**.
4. Find and resolve unsupported legacy `CREATE/ALTER` runtime self-healing code, Postgres schema-metadata probes, and literal `public` references under the Preview router. Verified live build, login, bank import, period list, posting, adjustment, date filters, posting period lock, and rollback must pass. Baseline lock stays enabled.
5. Freeze SOURCE writes through an approved maintenance window (not just a selected date); take a final consistent source snapshot, including journal and RK data, after outstanding write queues drain.
6. **Only with explicit change approval**, apply reviewed target schema SQL to `gpp_piutang` (never `public`). Inspect actual target DDL and ACL after applying and test that no other tenant or browser role has table privileges.
7. Securely export **original 22 source columns** with UUID and exact numeric precision using PostgreSQL client tools in an encrypted ephemeral operator environment. **Do not upload row values or hashes of passwords to GitHub, chats, or public logs.**
8. Import using an approved server-side migration with a scratch staging table, exact PK identity, rollback on duplicate-key content conflict, and an idempotent replay strategy. **Never blindly overwrite rows** and **never update POSTED journals**. If UUID exists in target, compare original-row digest; identical can be skipped, different MUST block the transaction for manual reconciliation.
9. Run both read-only fingerprint SQL files under maintained write freeze: require equal `row_count`, `unique_ids`, `debit_total`, `credit_total`, date bounds, and `content_sha256`. Then run per-ID set difference; empty difference required. The extra 3 target columns are outside the source digest.
10. Perform real authenticated E2E test with isolated data and test that GPP cannot read/modify BBM/CSB or Cabang data. Restore a tested backup on failure and keep old project active until all accepted.
11. Log the approval, commit SHA, migration execution ID, checksum, timestamp, and rollback evidence in a **private secure operator record** (no secrets in public repo).
12. Do NOT delete `vmpurwykfzcmculnnjfw` or any other legacy database until the entire two-BASE gate is PASS and explicit owner approval for destructive removal is received.

## Blockers that this DDL does NOT resolve
- Finance Preview credentials (tenant role passwords), write authority, and secure secret deployment.
- Vercel free-tier build-rate limit.
- GPP runtime SQL self-heal and metadata query integration tests.
- Import per CL journal sync bug (niyellll/project_piutang#127).
- Finance + Klarin complete backup/restore E2E; CSB Klarin six new attachments remain to be copied and checked.
- Current active-source delta sync and rollback.

**Status: STOP / NO-GO until all gates pass.** Source docs: niyellll/GPRO#8 and the live audit in this PR.
