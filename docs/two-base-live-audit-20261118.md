# Two-BASE migration — live audit and NO-GO gates
**Date:** 2026-11-18 (Asia/Jakarta)  
**Scope:** 7 existing Supabase projects → 2 target projects.  
**Mode:** read-only audit; **no DML, DDL, production change, secret disclosure, cost-bearing resource, or legacy deletion performed**.

## 1. Project status (verified from connected Supabase API)
All seven projects reported `ACTIVE_HEALTHY`.

| Target | Project ID | Function |
|---|---|---|
| bbm-finance | `fdhqidjltlihzdcbqfrd` | Finance: public, csb_finance, gpp_piutang, gpp_finance_cabang |
| bbm-klarin | `numlkqppirrxfwdhazja` | Klarin: public/klarin legacy, csb_klarin, gpp_stock |

Sources to retain: `vmpurwykfzcmculnnjfw`, `lmbvbgkqvidtkzxtvtpe`, `loodbfjkskduzqfthxxi`, `krwoiucqfcijmihnrlem`, `aupbqpdxiqulxcxeewri`.

## 2. LIVE exact table COUNT(*) audit
These are source versus target numbers read directly from each database, not row-level equality proof. Counts can change because source systems remain active. `COUNT`-matching tables are **NOT** proven data-identical. The scope is **92 matched table names**.

| Tenant | Matched tables | Count-equal | Count-different | Exact differences (source → target) |
|---|---:|---:|---:|---|
| CSB Finance | 35 | 33 | 2 | audit_logs 298→293; login_rate_limits 1→0 |
| GPP Finance Pusat | 22 | 20 | 2 | users 6→5; login_rate_limits 8→6 |
| GPP Finance Cabang | 22 | 21 | 1 | login_rate_limits 1→0 |
| CSB Klarin | 7 | 6 | 1 | klarin_stock_claim_attachments 6→0 |
| GPP Stock | 6 | 5 | 1 | klarin_sessions 0→2 |
| **Total** | **92** | **85** | **7** | |

### Non-matching table inventories (extra schema differences)
- GPP Finance Pusat source includes `public.rekening_koran_working_lines_v439` absent by name from target `gpp_piutang`; source holds **47 rows**, dated **2026-10-01 to 2026-10-31**. The target BBM `public` schema does contain a separate same-name table (25 columns vs 22 at GPP source), but **that is not proof of a GPP tenant migration and must not receive GPP rows inadvertently**. Treat as a potential missed business table until verified, even if a renamed target counterpart exists.
- The target Finance tenant schemas each include `gpro_v703_journal_archives_v1` not present by name in corresponding sources; do not drop or alter it without purpose/ownership investigation.

### Targeted identity audit without exposing credentials or usernames
- GPP Pusat user primary-key hashes show **all 5 target user IDs exist in source**, plus **1 source-only user ID**, whose created date is 2026-11-18. No password, username or raw user ID was exported or committed.
- CSB Klarin source holds **6 claim attachment metadata rows** created on 2026-11-18, total declared size **2,918,989 bytes**. All six have `storage_path`; all have empty `data_base64`. Their target tenant table is empty. These require private-object existence/ownership verification before incremental copy, with checksums and per-tenant authorization.
- Since source writes are still occurring, final reconciliation must use a controlled capture/freeze and **idempotent delta replay** without overwriting active sessions or creating journal duplicates.

## 2b. Full 92-paired-table content fingerprint audit (2026-11-18)
Used read-only SQL, per table: `md5(string_agg(md5(to_jsonb(row)::text), '|' ORDER BY row_md5))`, with a deterministic row-hash order. This detects differences in row values even where row counts match, but it is **not** a transactionally synchronized cross-project snapshot or a substitute for SHA-256 object backups, PK-based delta comparison, or audit review.

| Tenant | Digest-equal | Digest-different | Mismatch tables |
|---|---:|---:|---|
| CSB Finance | 32/35 | 3 | audit_logs, login_rate_limits, users |
| GPP Pusat | 20/22 | 2 | login_rate_limits, users |
| GPP Cabang | 20/22 | 2 | login_rate_limits, users |
| CSB Klarin | 4/7 | 3 | klarin_realtime_signal, klarin_stock_claim_app_state, klarin_stock_claim_attachments |
| GPP Stock | 4/6 | 2 | klarin_sessions, users |
| **TOTAL** | **80/92** | **12** | |

**Volatile user-session metadata diagnosis:** When hashing `users` without `active_session_id`, `active_session_expires_at`, `updated_at`, and `auth_session_version`, the digest is identical source vs target in CSB Finance, GPP Cabang, CSB Klarin, and GPP Stock; GPP Pusat remains mismatched because of the source-only new user. This does *not* authorize overwriting user sessions or account records. CSB Klarin app state and realtime signals remain volatile and require freeze/delta or explicit decision.

## 2c. Storage/backup metadata verified live
- Finance target `finance-private-backups`: **66 objects**, **13,211 bytes total**, **131–202 bytes per object**. These cannot be treated as demonstrated complete PostgreSQL backups.
- Klarin target `klarin-private-backups`: **67 objects**, **627,521,682 bytes total**, **2,390,790–20,665,356 bytes per object**. Content and full restore **unverified**.
- Klarin target legacy `klarin-private-attachments`: **888 objects**, **156,067,645 bytes total**.
- Klarin target tenant buckets `gpro-csb-private-attachments` and `gpro-gpp-private-attachments`: **no objects in inventory result**.
- Legacy **CSB** source: all six metadata attachment rows have matching physical `storage.objects` entries (6/6); the six files are still on the legacy source and **have not been copied to target**. Verify owner, object checksum, and access permissions before copy.

## 3. Roles, schema RLS, and Edge Functions
- Dedicated LOGIN roles on targets: `gpro_csb_finance`, `gpro_gpp_pusat`, `gpro_gpp_cabang`, `gpro_csb_klarin`, `gpro_gpp_stock`. All five have `rolpassword IS NULL`, `rolcanlogin=true`, `rolinherit=true`, `rolbypassrls=false`. **No real password-authenticated PostgreSQL connection test passed.**
- Tenant tables in target schemas have RLS enabled: CSB Finance 36/36, GPP Pusat 23/23, GPP Cabang 23/23, CSB Klarin 7/7, GPP Stock 6/6.
- Supabase `bbm-klarin` reports all six `gpro-{csb,gpp}-klarin-{auth,api,upload}` functions `ACTIVE`, `verify_jwt=true`. This **does not establish E2E login/upload or runtime staging availability**.
- `bbm-klarin` schema `klarin` has 3 physical tables with RLS disabled; verify whether they are exposed, what privilege grants apply, and whether this is expected legacy-only use before deciding any remediation.
- Supabase security advisor reports `rls_enabled_no_policy` on some public tables; **do not automatically grant broad access or disable RLS**. Backend can intentionally use server-side restricted authority.

## 4. Vercel branch-specific Preview verification
| Repository / purpose | Branch / SHA | Deployment / live status | Meaning |
|---|---|---|---|
| CSB Finance migration | `migration/two-base-csb-finance-v616` / `83425d91c736...` | `dpl_GKBPvHajwp1EAJWFz8mwAAwFBFSA` READY | Build only, no verified 2-BASE E2E |
| CSB Klarin migration | `migration/two-base-csb-klarin-20261116` / `8195c56afcc1...` | `dpl_nKvhdnvn5s2XcYT9i5xgPsiPBGGY` READY (staging) | Build only |
| GPP Klarin migration | `gpro-two-base-migration-20261116` / `3ab6b774b38b...` | `dpl_CPrY1tLUFFoU2YCgiXgwh6jjcUeY` READY | Old deployment, does not prove new env vars present |
| GPP Finance migration | `fix/two-base-preview-fail-closed-20261117` / `f23870faee58...` | `dpl_AHvMeS3t34fWuvhEexZ4UkV9u8Bc` READY | Fail-closed only |
| BBM Klarin migration | `gpro-two-base-migration-20261116` / `c586c4367dc5...` | `dpl_9fbkgiho9eJktc8V4DJqSUbHzRYs` READY | Build only |
| GPP Klarin single-workspace V722 | `feature/gpp-klarin-single-workspace-v722-20261118` / `bc021c902fa0...` | `dpl_9ehDEp2B1UX8HBUf3MUEpYRgxxVS` ERROR | Locked baseline rejects Pusat/Cabang isolation change |
| GPP Finance unified-login V725 | `feature/gpp-finance-unified-login-v725-20261118` / `48d11c7f4e2f...` | `dpl_8bTCobZyYNr7MXvDdDu3iba6ZgXu` ERROR | Root cause must be verified from complete logs |
| BBM Finance OPSPIRY design | `design/opspiry-visual-parity-20261118` / `5c78222a9915...` | `dpl_9MVdb2xB8pR9FQiSggCsnUjP4b11` ERROR | Global freeze reports changed `scripts/production-baseline-v615.json` |

**Do not conflate unrelated OPSPIRY design branches or main production READY with the correctness of migration Preview.** There is no evidence yet that all six current migration Previews incorporate intended branch-scoped environment variables or pass end-to-end tests.

## 5. Additional blocking feature defect
`niyellll/project_piutang#127`: `components/KartuExcelRestorePerClV597.tsx` imports **card rows only**. It sets `sudahDijurnal=false`, uses a row identity containing debit/credit amounts, and only appends to the card lists. Changes to existing amount risk a duplicate row; there is **no journal sync**. The separate V599 recovery creates DRAFT journals and must not be silently treated as POSTED reconciliation. Implement a reviewed, server-authorized atomic import design with stable IDs, conflict reporting, POSTED reversal policy, period locks, retry idempotency, and Piutang/Hutang regression cases. Do not modify locked production files without an approved baseline-safe change process.

`niyellll/GPP_STOCK#33`: V722 single-workspace removes existing warehouse isolation, forcing `gpp_pusat`. **Do not merge/promote this feature** until requirements, access matrix, and snapshots explicitly confirm the desired Pusat/Cabang isolation.

## 6. Next engineering gates, in order
1. Map each running app's actual backend/API route and Vercel branch-scoped database project ID; prove the connections point only to approved targets in Preview.
2. Audit JWT gateway + user session + `service_role` server-side authorization. Check `GPRO_KLARIN_STAGE_ENABLED` and route gates **without** enabling traffic prematurely. Verify tenant schema exposure, cross-tenant rejection, and role separation in an isolated test fixture.
3. Securely provision role credentials via approved secret management *if direct role login is genuinely required by application architecture*. Never print credentials or add broad DML grants to read-only roles.
4. Reconcile PK sets and deterministic content digests for **all tables**, including the GPP working-lines table, newer user, and 6 claim attachments. Distinguish business changes, sessions, login rate limits, audit logs. Append audit trail; no unsafe overwrite.
5. Verify full PostgreSQL + Storage backups and perform real isolated restore with checksum and RTO/RPO; private manifest JSON alone is insufficient.
6. Repair import per CL on a dedicated branch, keep baseline checks, validate full CI and cloud E2E.
7. After the above gates PASS, perform staged production cutover with health/rollback checks, then observe for legacy dependencies.
8. **Delete NONE of the five legacy projects without explicit owner approval after full PASS.** Avoid new billable environments and paid Vercel deployment quota bypass.

## Verification limitations
This report demonstrates current project status, catalog metadata, table counts, and Vercel deployment/build evidence. It is **not** a full data-content hash, authenticated database-login test, cloud E2E proof, Storage-object checksum test, restore test, safe-final-sync validation, or GO approval.

Related: https://github.com/niyellll/GPRO/issues/8 · https://github.com/niyellll/project_piutang/issues/127 · https://github.com/niyellll/GPP_STOCK/issues/33

## 7. Verified staging RPC defect and isolated code patch
- Connected Supabase `get_edge_function` confirmed deployed GPP stage-only functions `gpro-gpp-klarin-api` and `gpro-gpp-klarin-upload` contain an **undeclared `WORKSPACE`** argument to tenant RPC calls. These would throw at runtime if reached, rather than correctly selecting Pusat/Cabang.
- Fix source pushed **only** to `niyellll/GPP_STOCK` branch `fix/two-base-gpp-workspace-rpc-20261118` (based on the two-base migration branch): both RPC `p_workspace` arguments now come from `session.workspace`, which derives from authenticated warehouse session context.
- Added two static contract tests to the existing `tests/gpro-two-base-gateway-jwt-v1.test.mjs`, already referenced by `npm test`; manual source-contract assertions passed. **GitHub Actions Locked Baseline Gate (run 44327820390, SUCCESS; includes full regression + build) and GPRO Klarin Tenant Migration Safety (run 44327820131, SUCCESS) verified after patch; no real cloud E2E pass claimed**.
- Draft PR **https://github.com/niyellll/GPP_STOCK/pull/36**, head SHA `7a655d25b98974a69599d9a69d1be492e6aa44cd`. GitHub Actions CI successful, but Vercel status reports build-rate-limit failure; upgrade prohibited without permission.
- No Supabase Edge redeployment, staged flag activation, production update, baseline lock alteration or data mutation performed. Deployed runtime still contains bug until reviewed fix is safely rolled out.

## 8. GPP Finance RK schema and fingerprint package (review only, not executed)
- Source `public.rekening_koran_working_lines_v439` has **47 distinct UUIDs** in 47 records. LIVE read-only SHA-256 query succeeded. The column inventory has **22** source columns; the staged finance app bank routes expect **25** columns when optional `matched_journal_no`, `matched_source`, `attachment_note` are included.
- The target `gpp_piutang` schema has neither the RK V439 table nor the V543 period metadata table; source also has no V543 period table. App routes currently expect both tables to exist or try to create them at request time.
- The GPP two-base Preview's `lib/gproFinanceSqlRouterV2.mjs` is designed to remap lexically qualified `public.*` SQL identifiers into `gpp_piutang`/`gpp_finance_cabang` and reject several problematic SQL literals. This means the existence of `public.*` in route source is **not sufficient to assert actual BBM data mixing while the Preview router is active**, but the SQL remapper, runtime DDL, and literal metadata probes are **not cloud E2E tested** and may cause fail-closed runtime errors.
- Prepared **NOT APPLIED**: `ops/sql/gpp_piutang_rekening_koran_v439_create_REVIEW_ONLY.sql` (25-column target V439, V543 metadata, indices, RLS, read-only GPP Pusat grant and cross-tenant checks). No user data embedded. Deliberately aborted if target tables already exist or roles are missing.
- Prepared `ops/sql/gpp_rk_source_fingerprint_READ_ONLY.sql` and `ops/sql/gpp_rk_target_fingerprint_READ_ONLY.sql`: deterministic SHA-256 using the original 22-column projection, row count, UUID count, aggregate debit/credit, and date bounds.
- Tested source fingerprint SQL directly against legacy GPP project: **47 rows, 47 unique UUIDs**, date range October 2026, SHA-256 computed successfully. Target query **cannot pass yet because the required tenant table does not exist**.
- Seven static source-contract checks passed on staged SQL files (correct target schema, 25 columns, V543 table and RLS, select-only tenant role, matching digest projection, fail-closed/no import). **This is not SQL execution or integration testing.**
- Full prerequisites and explicit NO-GO controls: `ops/runbooks/GPP_FINANCE_RK_V439_CUTOVER_NO_GO_20261118.md`. Current storage and finance full restore unproven; no schema change or delta import performed.

## 9. Guarded RK transfer utility and offline CI
- Added **`ops/scripts/gpp_rk_transfer_guarded.py`** as a default read-only guarded transfer helper. No DB connection strings, passwords, customer records or source transactions are committed to code.
- `--apply` is explicitly gated on an approved change reference, verified restore reference, freeze confirmation, expected SHA-256 and expected record count. SQL reads a stable original 22-column projection from source; source/target project refs are checked; target RLS/ACL and UUID conflicts are checked; inserted rows are audited by SHA-256 inside a transaction prior to commit. **External freeze and restore evidence remain manual operator prerequisites**; this code has not been connected to credentials or run on the target.
- Added **9 offline no-network unit tests** at `ops/tests/test_gpp_rk_guarded.py` and a dedicated limited GitHub Action `.github/workflows/gpp-rk-guarded-offline.yml`. No database access or secrets are required by tests.
- **Verified CI PASS:** GitHub Actions `GPRO guarded RK transfer offline checks` run `44338607838` completed SUCCESS; Python syntax compilation and all **9/9 offline unit tests** passed according to job `134922032681` logs. This is NOT authenticated source/target E2E.

## 10. CSB Klarin claim + attachment business delta (live)
- Read-only source and target SHA-256 key-level inventory was executed using `ops/sql/csb_klarin_state_source_READ_ONLY.sql` and `ops/sql/csb_klarin_state_target_READ_ONLY.sql`.
- Source `default` app state version **40**, target **38**; both have 21 JSON keys. **18 keys equal**; three differ: `monitoringKlaim` 4→0, `uploadBatches` 2→1, `auditLogs` 39→37 (source→target).
- Within those arrays, multiset comparisons of per-item JSON digests found **7 source-only items, 0 target-only items** (4 claim records + 1 batch + 2 audit entries). These are provisional read-only snapshot results, not an atomic final sync. In addition six physical CSB attachment objects must move with owner-aware metadata.
- Added `ops/runbooks/CSB_KLARIN_CLAIM_DELTA_NO_GO_20261118.md` to specify backup-first, Storage object hash, optimistic versioning, append-only audit, scoped claims and conflict-safe merge. No data was written.

## 11. Audit log and signal delta checks
- CSB Finance `public.audit_logs` source **298** vs `csb_finance.audit_logs` target **293**; per-row JSON fingerprint multiset **5 source-only, 0 target-only**. Target audit history is a subset at this observation time. Future replay must be append-only and idempotent, preserve actor/time/event references and avoid copy of active login metadata.
- CSB Klarin `klarin_realtime_signal` source `default` version **40** vs target **38**, corroborating state version gap. Do not update the signal to 40 without a safe state + attachment transfer and authorized E2E.

## 12. Validated CSB attachment ownership and strengthened offline release gate
- Verified source `klarin_stock_claim_attachments`: **6/6 unique metadata IDs**, **6/6 unique object paths**, **all 6 attached to one valid claim** among the four missing claim records, **6/6 matching Storage path and object size**, **6/6 empty inline Base64**, total **2,918,989 bytes** (four PDF + two XLSX). Target CSB tenant bucket/private metadata still **0 objects/rows**.
- Source `monitoringKlaim`, `uploadBatches`, `auditLogs` stable business IDs are unique and nonempty (4/2/39). Target corresponding arrays have 0/1/37 entries. No content migration and **no physical byte SHA-256 download** performed.
- `ops/sql/csb_klarin_claim_attachment_source_READ_ONLY.sql` and `ops/sql/csb_klarin_claim_attachment_target_READ_ONLY.sql` **executed successfully on their actual separate projects**, and tenant bucket remains private with RLS/no browser SELECT for claim metadata.
- Added **read-only offline CSB delta planner** `ops/scripts/csb_klarin_claim_delta_plan.py`, checks same ID changed content, target-only entries, unrelated state changes, stable claim owner, duplicate file path, size mismatch, path traversal and supplied object hashes. This planner has NO network/write mode; source snapshots remain private and were not exported to the PR. `ops/tests/test_csb_klarin_claim_delta_plan.py` includes **13 synthetic tests**.
- Combined offline safety workflow compiled both tools and all **22/22 tests PASS**, most recently GitHub Actions run `44346353062`, job `134949678701`. These are not database/Storage E2E tests.
- GPP RK original-source fingerprint query now **explicitly lists exactly 22 source fields**, protecting the audit against future target-only columns. Reexecuted on live source and obtained **47 rows/47 unique IDs** and **SHA-256 identical to the earlier run**. Matching Python guarded-transfer fingerprint and regression tests updated; 22/22 final CI PASS.
- Supabase Security Advisor for two targets only reported INFO-level `rls_enabled_no_policy` notices in preexisting `public` tables (Finance 10, Klarin 6). No other lints reported in these checks. RLS without a policy is deny-by-default; do not add public grants to silence INFO advisories. [Guidance](https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy).

**Still NO-GO:** fully restored backups, secret-backed roles, private byte hashing, authorized Storage transfer, claim app-state optimistic concurrency, actual isolated E2E, final frozen audit and formal cutover.

## 13. Original private Storage byte-audit tool and restore gate (19 Nov)
- Added `ops/scripts/csb_klarin_storage_byte_audit.py` (standard library only, offline, no DB/network/write) with `ops/tests/test_csb_klarin_storage_byte_audit.py`. The tool hashes real local source/target files, compares SHA-256 byte-for-byte, checks expected filename-independent object count and total bytes from a write-frozen inventory, rejects path traversal, duplicate object identity, symlinks, missing/wrong-size files and unsupported MIME. Its output is aggregate-only and ALWAYS `ready_for_cutover=false`.
- Source-only mode explicitly reports **no target verification**. Counts of independently supplied expected SHA-256 proofs are separate from locally calculated digests; a missing trusted digest is not reported as authenticated proof.
- CI **GitHub Actions run `44355430227`** after the new frozen-count/hash-proof guards: Python compilation **SUCCESS**, **37/37 offline synthetic unit tests PASS**, job `134982145788`. This validates tooling, NOT real PDF/XLSX content or cross-cloud sync.
- Fresh read-only source/target data checks confirm **CSB Klarin source v40 vs target v38**; source 4 claims/2 batches/39 app-audit/6 physical attachments, target 0 claims/1 batch/37 app-audit/0 CSB tenant attachments. GPP RK remains 47 source rows / missing target RK and V543 tables. These counts are NOT a frozen transaction checkpoint.
- Fresh read-only bucket inventory: Finance `finance-private-backups` 66 objects, max 202 bytes; Klarin `klarin-private-backups` 67 objects, max 20,665,356 bytes. Real database restore and storage-object byte integrity are **still NOT proved**.
- Fresh catalog read: **all five dedicated tenant LOGIN roles have no stored password** (3 Finance, 2 Klarin). These roles cannot be assumed to support authenticated E2E. **No password was read, reset or exposed.**
- Added `ops/runbooks/TWO_BASE_BACKUP_RESTORE_GATE_NO_GO_20261119.md`: official Supabase roles/schema/data dump + separate Storage bytes, independent restore in existing isolated test environment, E2E and rollback, no paid project or production restore. Neither GitHub tests nor backup bucket markers satisfy that release gate.

**Release decision remains NO-GO; all five legacy projects preserved.**

## 14. Finance V635 anon staging privilege exposure + five-role matrices (19 Nov)
- Read-only live SQL confirms Finance `public` contains **9 empty legacy V635 staging tables**. Each has RLS enabled, a **direct `anon INSERT` grant**, exactly one anonymous INSERT policy with a **fixed migration-key condition**, and **no `anon SELECT`**. This is a potential anonymous write surface if the public Data API route is exposed and the static value can be satisfied; **no actual external exploit was tested or confirmed**. Never quote the static key publicly.
- `ops/sql/bbm_finance_v635_staging_anon_acl_READ_ONLY.sql` was **actually executed and verified** on `fdhqidjltlihzdcbqfrd`. `ops/sql/bbm_finance_v635_stage_revoke_anon_REVIEW_ONLY.sql` was **prepared but NOT applied**. The proposed script takes writer-excluding locks, checks exactly nine tables still empty/RLS/grants, revokes only anon INSERT, checks server privileges are preserved and otherwise rolls back. It does not drop a table, alter tenant records or change production until separate operator authorization and full backup/restore gate PASS.
- Finance tenant matrix `ops/sql/two_base_finance_tenant_role_gate_READ_ONLY.sql` **executed** on target. `gpro_csb_finance` can SELECT 36/36 CSB tables; `gpro_gpp_pusat` SELECT 23/23 GPP Pusat; `gpro_gpp_cabang` SELECT 23/23 GPP Cabang. Each has 0 cross-schema table SELECT, 0 own INSERT/UPDATE/DELETE, all expected tables RLS on, and **no password set**.
- Klarin tenant matrix `ops/sql/two_base_klarin_tenant_role_gate_READ_ONLY.sql` **executed** on target. `gpro_csb_klarin` can SELECT 7/7 tenant tables, `gpro_gpp_stock` SELECT 6/6. Both have 0 cross-schema SELECT, 0 own INSERT/UPDATE/DELETE, all expected tenant tables RLS on, and **no password set**. Klarin roles have `public` schema USAGE but **no `public` table SELECT**; therefore schema USAGE alone is not an exposure finding.
- Routine privilege checks: **no callable `SECURITY DEFINER` functions for any of the five tenant roles** within the selected public/tenant schemas. Finance public schema owns 62 SECURITY DEFINER routines but current tenant roles cannot execute them; Klarin public + CSB tenant have an inaccessible one each. This is limited catalog evidence and not an E2E probe.
- `bbm-klarin.public.klarin_realtime_signal` is deliberately review-flagged: anon/authenticated can SELECT metadata `workspace_key/version/updated_at` through a `USING (true)` policy. Do not revoke without first verifying realtime client dependency. Private CSB/GPP claim signal tables are not given browser grants.
- `ops/runbooks/BBM_FINANCE_V635_ANON_STAGING_SECURITY_NO_GO_20261119.md` and `ops/runbooks/TWO_BASE_TENANT_ROLE_GATE_NO_GO_20261119.md` provide separate review and safe writer design prerequisites.
- **GitHub Actions run `44360177841`, job `134999056031`, SUCCESS: 50/50 offline synthetic/static unit tests PASS**. New tests cover staging ACL scope, locked preflight, non-secret fixed-query role matrix, and no unauthorized SQL grant/DML.
- This does **not** fix Finance Preview app writes: the five dedicated logins are deliberately read-only; real authenticated, auditable server-side per-tenant write authorization and proper role secret handling remain NO-GO. The full 7-project PostgreSQL+Storage backup/restore drill is still missing.

**Decision: NO-GO. No production SQL privilege change executed, no paid deployment or legacy deletion.**

## 16. CSB Klarin guarded state CAS + original private Storage byte parity (19 Nov)
- Updated `ops/scripts/csb_klarin_claim_delta_plan.py`: `merged_state_from_verified_subset` now creates a **private, in-memory, exact source-order state merge** from validated ID-matching subsets; preserves pre-existing matching target objects and refuses target-only IDs, duplicate IDs, same-ID content conflicts, changed non-delta keys and inconsistent versions. Never prints customer data.
- New `ops/scripts/csb_klarin_state_transfer_guarded.py` is **DRY RUN BY DEFAULT**, limited to pinned legacy `krwoiucqfcijmihnrlem` → `bbm-klarin` BASE `numlkqppirrxfwdhazja` / `csb_klarin`. A separately approved apply requires tested full 7-project backup+restore, external source write-freeze, pinned and authenticated operator credentials, exact source+target version and state SHA-256, original source and target private file trees and independent SHA-256 proofs for **all** files, and an approved change ID. It does **not** upload/copy Storage objects automatically; staged objects must already be in the dedicated private target bucket. It then validates all three tenant tables, every individual server CRUD grant, RLS, cross-tenant/anon denial, exact Storage metadata path+size, CAS version+state and realtime signal, and appends only missing attachment IDs. No overwrite or deletion; on any check failure rolls back the target DB transaction.
- New `ops/tests/test_csb_klarin_state_transfer_guarded.py` has 15 synthetic tests including true local source+target byte SHA-256 parity with a modified-file rejection. Three further tests cover exact in-memory claim merge. **GitHub Actions run `44461815980`: 84/84 offline safety tests PASS**; script compilation SUCCESS. This does **not** prove real customer attachment transfer.
- Two reviewed **aggregate-only** SQL `ops/sql/csb_klarin_source_locked_snapshot_READ_ONLY.sql` and `ops/sql/csb_klarin_target_locked_snapshot_READ_ONLY.sql` both executed successfully against separate live projects. Source currently version **40**, 21 state keys, 4 claim/2 batch/39 audit entries, six private attachments (2,918,989 B), exact `state::text` SHA-256 `ed2484691d19350379127452d496a6ddbcaf57ba371fabf8c75937154eeb698c`; target version **38**, 21 state keys, 0 claim/1 batch/37 audit, no attachment objects, state SHA-256 `2da0b30b5641558ddc39098e548e3b1f563233f4e6398ffcd2608a89e5726303`. These are **historical read-only observations, not an authenticated frozen snapshot**; do not use them blindly to authorize `--apply`.
- [Operator runbook](https://github.com/niyellll/GPRO/blob/audit/two-base-live-reconciliation-20261118/ops/runbooks/CSB_KLARIN_STATE_CAS_OPERATOR_NO_GO_20261119.md) documents private Stage → verified readback → guarded Postgres CAS → app E2E → separate approved cutover and rollback. Real Storage bytes have not been copied; target bucket remains empty. No live DML, privileged role changes, Vercel secret operations, or legacy project deletion.

**NO-GO:** seven→two consolidation is still blocked by full PostgreSQL+Storage restore proof, staged real files, tenant writer/session E2E, GPP Finance baseline V615, fresh final source freezes and approved cutover.

## 17. Real PostgreSQL 17 synthetic CAS and GPP Finance runtime-coverage blocker (19 Nov)
- `ops/sql/EPHEMERAL_CSB_KLARIN_CAS_TEST_ONLY.sql` runs against a **disposable** PostgreSQL 17 service in GPRO GitHub Actions: creates synthetic CSB/GPP roles and RLS-enabled tables, checks cross-tenant and anonymous privilege denial, commits version/state CAS 38→40 and realtime update with attachment metadata, rejects stale version 38 update, and verifies rollback leaves no partial state/attachment. It is NOT executed on either Supabase BASE.
- The existing workflow now has **two separate green jobs**, latest [run 44462221527](https://github.com/niyellll/GPRO/actions/runs/44462221527): **84/84 Python offline synthetic tests PASS**, and real ephemeral PG17 logs end with `CSB_KLARIN_EPHEMERAL_PG17_CAS_PASS`. App/physical Storage E2E remains unproven.
- Reviewed detailed GPP Finance migration preflight runtime inventory [run 44459429769](https://github.com/niyellll/GPP_PIUTANG/actions/runs/44459429769): 198 runtime source files scanned, 52 matching DB-related files, **25 potential** raw connection/pool bypass markers. These are audit candidates, **not proof of 25 exploitable vulnerabilities**: inspected admin, accounting, journal, piutang and bank reconciliation handlers include explicit two-BASE Preview 503 or fail-closed protections. Consequently those guarded finance features are **not yet functional** against the consolidated BASE. Preflight/build passing only proves gates/compile, not full business-operation compatibility.
- Verified by read-only SQL on both Finance BASE tenant schemas **and both legacy GPP source projects**: `bank_reconciliation_sessions_v162`, `bank_reconciliation_matches_v162`, and `bank_statement_lines_v162` are **not present** in the inspected source/target schemas. Do not enable the Preview bank reconciliation handler and claim it works; a reviewed schema definition/migration and per-tenant E2E is required for first-use support.
- Do NOT solve this by letting dedicated read-only Finance tenant roles run runtime `CREATE TABLE`, issuing unrestricted `service_role` browser tokens, or disabling the SQL-router Preview guards. Preserve journal posting/period-lock/reversal and Pusat/Cabang tenant isolation until authenticated server-only scoped writers and a full validated database schema are demonstrated.

**NO-GO cutover remains in force; two permanent BASEs are active and all five old projects preserved.**
