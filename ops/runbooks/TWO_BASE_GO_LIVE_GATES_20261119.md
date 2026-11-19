# GPRO migration 7 Supabase projects → 2 BASEs: production readiness gates
**Status: NO-GO for changing production authority.** Read-only evidence checked 19 Nov 2026 Asia/Jakarta; source databases remain active. This document is a precise execution checklist, NOT permission to delete any legacy database or bypass CI/backup.

## Destination ownership (two existing ACTIVE_HEALTHY BASEs)
| Destination | Supabase project | Tenant schema | Application |
|---|---|---|---|
| BBM Finance | `fdhqidjltlihzdcbqfrd` | `public` | BBM Finance |
| BBM Finance | same | `csb_finance` | CSB Finance |
| BBM Finance | same | `gpp_piutang` | GPP Finance Pusat |
| BBM Finance | same | `gpp_finance_cabang` | GPP Finance Cabang |
| BBM Klarin | `numlkqppirrxfwdhazja` | `public` / legacy `klarin` | BBM Klarin |
| BBM Klarin | same | `csb_klarin` | CSB Klarin |
| BBM Klarin | same | `gpp_stock` | GPP Klarin / Stock |

Do **not** assume two ACTIVE_HEALTHY projects means the migration is complete. Keep five legacy sources fully active with separate recoverable backups.

## Verified software gates
| Gate | Evidence / result | Decision |
|---|---|---|
| GPRO offline migration safety | [Actions 44459802002](https://github.com/niyellll/GPRO/actions/runs/44459802002) **66/66 pass** | PASS offline only |
| GPP Finance Preview pooler role | [Draft PR #27](https://github.com/niyellll/GPP_PIUTANG/pull/27) preserves dedicated `gpro_gpp_pusat` or `gpro_gpp_cabang`, refuses admin downgrade and insecure URLs | PASS focused regression |
| GPP Finance existing migration preflight | [Actions 44459429769](https://github.com/niyellll/GPP_PIUTANG/actions/runs/44459429769) app tests, build, TypeScript, SQL router and ephemeral PostgreSQL 17 isolation **SUCCESS** | PASS preflight |
| GPP Finance locked release baseline | Quality Gate V615 refused repository source change; do not alter existing manifest merely to silence it | FAIL release |
| GPP Finance Rekening Koran runtime DDL | PR #27 now checks tenant table and 32 required columns in Preview rather than silently CREATE/ALTER; normal legacy route unchanged | PASS code, FAIL live tables |
| GPP Stock workspace RPC | [Draft PR #36](https://github.com/niyellll/GPP_STOCK/pull/36) locked baseline / tenant safety checks passed on branch | PASS review only |
| Vercel Preview two-BASE routing | GPP Finance lacks `GPRO_FINANCE_PREVIEW_DATABASE_URL`, `GPRO_FINANCE_PREVIEW_DATABASE_URL_CABANG`, `GPRO_TWO_BASE_FINANCE_ROUTING_READY` for migration branch | FAIL |
| Database tenant role read isolation | Finance 36/23/23 tables; Klarin 7/6 tables; 0 cross-schema table SELECT, all tenant tables RLS | PASS catalog only |
| Actual database tenant LOGIN | All 5 dedicated LOGIN roles have no configured password; no authenticated user connection E2E | FAIL |
| Server-side application writer | Tenant logins have 0 INSERT/UPDATE/DELETE; no approved, restricted, authenticated writer pathway verified | FAIL |

## Real data still requiring reconciliation (unfrozen read-only snapshots)
1. **GPP Finance Pusat**: 47 source-only Rekening Koran rows; tenant `gpp_piutang.rekening_koran_working_lines_v439` and `rekening_koran_period_meta_v543` missing. Source 47 unique UUID; initial source SHA-256 68a1241428c9d92d90ca1f2ee0354000ad41767ac7a558c9f07270e54b8c6904. Source user and login-session differences also pending; never blindly copy logins/sessions.
2. **CSB Finance**: 298 source `public.audit_logs`, 293 target `csb_finance.audit_logs`. Read-only SHA-256 per UUID matches all 293 common records: **5 source-only, 0 target-only, 0 conflicts**. Source full-set checksum `4c11d7e82d912d543ad79f1b6d2f3acafa2dfa3d4a61877c228a68c7b4c4f69f`; target full-set `704ac36097a0d45147cd871973bde32cbc1fd02fb3ef5285b94b7c53631fc670`. These are **not frozen**, so recompute after sign-off.
3. **CSB Klarin**: source app state version 40 (4 claim records, 2 upload batches, 39 audit events), target version 38 (0 claim records, 1 batch, 37 audit events). 18 other JSON state keys match. Six legacy claim attachments (4 PDFs, 2 XLSX), 2,918,989 bytes, source private objects present; target CSB dedicated private bucket empty. Physical file SHA-256 and owner-aware import not completed.
4. **GPP Stock / other**: volatile sessions, audit metadata and login rate limits differ. Remaining 92-table full consistency check must be refreshed after source freeze; prior count parity 85/92 and per-table hash parity 80/92 is **not** a final cutover proof.

## Non-negotiable safe production sequence
**A. Backup + actual restore evidence** — A named authorized operator exports all seven PostgreSQL projects (roles/schema/data) and separate Storage private objects with byte SHA-256; restores both successfully in an *already available isolated test environment*, verifies row counts/constraints/RLS/auth/storage and records encrypted backup locations. Do not create paid resources or fake proof. See [restore runbook](TWO_BASE_BACKUP_RESTORE_GATE_NO_GO_20261119.md).

**B. Tenant credentials and server-only writers** — Admin privately creates least-privilege named credentials, stores them in Vercel **Preview** secrets for the exact migration branches, never in GitHub/chat. Retain distinct role identities and server request/tenant authorization. Do not grant global table writes to the five read-only accounts; implement and verify restricted writes with audit/period locks and all cross-tenant negative tests. Keep Preview flag off until these checks pass.

**C. Finish schema and object deltas** — After approved restore/review/freeze:
- Apply GPP RK and period *reviewed DDL* only to `gpp_piutang`, then use `ops/scripts/gpp_rk_transfer_guarded.py` with new fingerprint (expected 47). Never touch `public` BBM RK.
- Run `ops/scripts/csb_finance_audit_transfer_guarded.py` dry-run, then approved append-only transfer of 5 immutable audit UUIDs with server CRUD verified **individually**.
- Export and transfer actual CSB Klarin attachments through private authenticated Storage, verify object SHA-256 with `ops/scripts/csb_klarin_storage_byte_audit.py`, link metadata to the correct claim and only then advance app state under version-CAS. No blind state overwrite or dropped audit logs.
- Reconcile missing business users and volatile login/session tables by explicit field-level policy; do not overwrite active sessions.

**D. Pre-release checks** — New app migration branch builds must pass original golden baseline or separately reviewed new baseline version and repository hygiene; all APIs must pass authenticated read and write, browser/API tenant-denial, journal posting/unposting, lock periods, upload/replace/retur, download/private attachment, errors/rollback and regression scenarios. Respect Vercel plan build quotas; never bypass by upgrading without user agreement.

**E. Approved cutover + rollback** — Freeze legacy writes, take final consistent source+target hashes, apply only missing idempotent deltas, ensure atomic transactions per tenant and verified storage bytes, switch production connection authority via reviewed env+deployment, monitor error/ledger drift, retain a tested rollback path. **Keep all five legacy Supabase projects** until owner explicitly and separately authorizes deletion after the retention/rollback window.

## STOP criteria
Any restore failure, source/target checksum drift, missing physical object, tenant cross-read, unauthorized writer, broken token, failed accounting baseline, Vercel build error, missing locked period or application E2E means **NO-GO**. Passing static/ephemeral CI is necessary but **not** sufficient.

## Open review work
- [GPRO #9](https://github.com/niyellll/GPRO/pull/9) — migration scripts, SQL evidence, and safety runbooks (draft).
- [GPP Finance #27](https://github.com/niyellll/GPP_PIUTANG/pull/27) — preserve pooler tenant identity; Preview bank route without runtime DDL (draft).
- [GPP Stock #36](https://github.com/niyellll/GPP_STOCK/pull/36) — GPP Klarin workspace RPC isolation (draft).
