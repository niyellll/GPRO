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
- GPP Finance Pusat source includes `public.rekening_koran_working_lines_v439` absent by name from target `gpp_piutang`; source holds **47 rows**, dated **2026-10-01 to 2026-10-31**. Treat as a potential missed business table until verified, even if a renamed target counterpart exists.
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
- Added two static contract tests to the existing `tests/gpro-two-base-gateway-jwt-v1.test.mjs`, already referenced by `npm test`; manual source-contract assertions passed. **No Node test run or real cloud E2E pass claimed**.
- Draft PR **https://github.com/niyellll/GPP_STOCK/pull/36**, head SHA `7a655d25b98974a69599d9a69d1be492e6aa44cd`. CI status from Vercel reports build-rate-limit failure; upgrade prohibited without permission.
- No Supabase Edge redeployment, staged flag activation, production update, baseline lock alteration or data mutation performed. Deployed runtime still contains bug until reviewed fix is safely rolled out.

