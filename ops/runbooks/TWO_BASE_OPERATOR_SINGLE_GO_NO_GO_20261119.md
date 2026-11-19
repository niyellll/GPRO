# Seven Supabase projects → two BASEs: one operator GO/NO-GO check

**Last reviewed 19 November 2026, Asia/Jakarta.** This runbook cannot authorize deletion or cutover. The requested final state is exactly `bbm-finance` and `bbm-klarin`, with all existing businesses and customers still able to sign in and transact.

## What is actually true now

Both target projects already exist, but **seven Supabase projects still show ACTIVE_HEALTHY**. Current read-only live inventory:

| Tenant | Legacy source | Destination tenant schema | Remaining functional gap |
|---|---|---|---|
| CSB Finance | `lmbvbgkqvidtkzxtvtpe` | `fdhqidjltlihzdcbqfrd.csb_finance` | 298 legacy audit rows; 293 target (5 missing) |
| GPP Finance Pusat | `vmpurwykfzcmculnnjfw` | `fdhqidjltlihzdcbqfrd.gpp_piutang` | 6 source users; 5 target (1 missing); 94 RK rows already staged |
| GPP Finance Cabang | `loodbfjkskduzqfthxxi` | `fdhqidjltlihzdcbqfrd.gpp_finance_cabang` | protected app write-path / tenant login not proven |
| CSB Klarin | `krwoiucqfcijmihnrlem` | `numlkqppirrxfwdhazja.csb_klarin` | 6 source physical private objects / 0 target; 6 attachment metadata / 0; app state 40 / 38 |
| GPP Stock | `aupbqpdxiqulxcxeewri` | `numlkqppirrxfwdhazja.gpp_stock` | authenticated workspace JWT, writer and regression test not proven |

BBM Finance/Klarin original live applications remain in the `public` schemas of their respective target BASE projects. The five dedicated tenant PostgreSQL LOGIN roles exist and have RLS, but **none of their passwords are configured yet**. Their role definitions are read-only by design; never grant all tenants unrestricted table UPDATE to make the app work.

This is a **cross-region migration**: CSB Finance/Klarin legacy projects are in Singapore (`ap-southeast-1`), the target BASEs are in Mumbai (`ap-south-1`). Obtain the responsible data controller's permission before cross-region customer data movement.

## Single executable preflight: no writes, no deletion

`ops/scripts/two_base_live_readiness_gate.py` is a combined **read-only, fail-closed** seven-project audit. It checks:

- actual full-table row-count and **sorted per-row SHA-256 multiset parity** for every common tenant table; unmatched source tables, schema drift and mismatched business contents block data-parity readiness;
- treats **`login_rate_limits` and `klarin_sessions` as volatile session controls**, reports their drift separately rather than silently overwriting them;
- for `users`, compares stable account identity/credential/role/creation data while *separately* requiring actual session reauthentication E2E; no user values, UUIDs or hashes are printed;
- tenant schema RLS, own-role SELECT, browser deny, and **other tenant-role SELECT denied**;
- five dedicated LOGIN roles and whether their passwords have been configured (boolean only);
- private **CSB Klarin** bucket count/metadata bytes in the pinned source and target bucket (this is only metadata, NOT proof of physical object bytes).

**Default invocation** performs **zero network connections** and outputs only required environment variable names:

```powershell
python ops/scripts/two_base_live_readiness_gate.py
```

The live form runs only on an authorized operator-controlled computer using Python 3.10+ and `psycopg[binary]`, with seven private, separately project-pinned connection strings (one per Supabase project). Prefer securely managed environment variables or an operating-system secret manager; **do not paste DSNs/passwords into the terminal history, this chat, GitHub, .env files committed to the repo, or CI**:

| Required environment variable | Project |
|---|---|
| `GPRO_BASE_FINANCE_PG_DSN` | `fdhqidjltlihzdcbqfrd` |
| `GPRO_BASE_KLARIN_PG_DSN` | `numlkqppirrxfwdhazja` |
| `GPRO_CSB_FINANCE_OLD_PG_DSN` | `lmbvbgkqvidtkzxtvtpe` |
| `GPRO_GPP_PUSAT_OLD_PG_DSN` | `vmpurwykfzcmculnnjfw` |
| `GPRO_GPP_CABANG_OLD_PG_DSN` | `loodbfjkskduzqfthxxi` |
| `GPRO_CSB_KLARIN_OLD_PG_DSN` | `krwoiucqfcijmihnrlem` |
| `GPRO_GPP_STOCK_OLD_PG_DSN` | `aupbqpdxiqulxcxeewri` |

Only PostgreSQL owner-form direct URLs (`postgres@db.<exact-project-ref>.supabase.co:5432/postgres`) or pinned per-project Supavisor owner session-pooler URLs (`postgres.<exact-project-ref>@...pooler.supabase.com:5432/postgres`) are accepted, with SSL `require` or `verify-full`. Owner access is used **only to see all tenant tables and role credential booleans**. Every connection is opened in a **REPEATABLE READ READ ONLY** transaction, never using DML/DDL, and rolled back and closed.

After ALL seven projects are in a verified application-write freeze and a full backup **plus a real independent restore drill** exists, run:

```powershell
python ops/scripts/two_base_live_readiness_gate.py --live
```

The output contains only counts, schema/table names, status flags and aggregate drift—not raw accounting/user rows, object paths, passwords or decrypted credentials. It can be saved privately and attached as a **redacted aggregate checkpoint** to an approved change ticket. Its `cutover_ready` and `delete_or_pause_legacy_projects` deliberately remain `false` even if SQL parity passes, because SQL metadata cannot prove physical Storage bytes, restore success, authorization or app E2E.

**Important:** seven independent SQL snapshots are not an atomic distributed snapshot. A live parity result is provisional unless a separate **verified write freeze across all seven projects** exists.

## Actual operational sequence required to reach only two project cards

1. **Backup and independent restore:** Back up PostgreSQL roles/schema/data for all seven projects using the [current Supabase CLI backup/restore guide](https://supabase.com/docs/guides/platform/migrating-within-supabase/backup-restore). Export **actual Storage bytes separately**: [Supabase database backups](https://supabase.com/docs/guides/platform/backups) do not include file bytes. Run a successful test restore in an already available isolated nonproduction environment. Archive and verify checksums, passwords and auth restoration privately; no new paid resource without owner approval.
2. **Real private attachments:** For CSB Klarin, use `csb_klarin_private_manifest_guarded.py` to derive SHA256 from all six original private bytes, `csb_klarin_storage_stage_guarded.py` for no-upsert private upload and exact readback, then `csb_klarin_state_transfer_guarded.py` for metadata and atomic version-CAS state update. Total inventory currently 2,918,989 bytes; do not reuse counts without a new write-frozen audit. Do not accidentally copy them into the BBM target bucket.
3. **Immutable finance deltas:** Use `csb_finance_audit_transfer_guarded.py` for the five missing UUID log events and `gpp_pusat_user_delta_guarded.py` for the one missing user. Both are read-only by default, forbid overwriting shared records, and require backup/restore/freeze and authenticated operator approval for any write. Clear stale sessions and verify login; never copy volatile sessions blindly.
4. **Application authority and Preview:** Configure restricted private **Preview** credentials for CSB Finance, GPP Pusat/Cabang, CSB Klarin and GPP Stock. Verify browser/tenant scope, server writer grants, all journal and stock CRUD, private downloads and negative cross-tenant tests. GPP Finance PR #27 is still blocked by locked V615 baseline; handle through an explicitly approved baseline release, not bypass. Respect Vercel build quotas.
5. **Cutover and rollback:** Run this seven-project census against frozen sources and targets, verify actual original/target Storage bytes and restored backups, complete a reviewed application cutover with tested rollback, monitor ledgers, and **retain the five old projects during the approved retention window**.
6. **Only after separate owner decommission approval**, use Supabase Dashboard project deletion to reduce organization project cards from seven to two. The current connected Supabase tools expose **pause**, not project deletion. Pausing does not make cards disappear and can cause application outages.

## STOP / NO-GO conditions

Any missing audit event/user/claim, backup or restore drill not demonstrated, private original/target SHA mismatch, RLS or tenant cross-read, role unable to authenticate, incomplete server-only writer paths, unverified journal/stock reconciliation, failed frozen baseline or Vercel deployment, or unapproved cross-region data transfer must **stop** cutover and project deletion.

**Owner decision remains NO-GO** until every gate is independently proven. Keep sensitive project access only in private operator tools. For management tracking see [GPRO issue #8](https://github.com/niyellll/GPRO/issues/8).
