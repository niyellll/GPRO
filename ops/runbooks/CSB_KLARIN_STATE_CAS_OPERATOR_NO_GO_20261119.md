# CSB Klarin — guarded claim state + attachment CAS transfer (reviewed, NOT RUN)
**Operator instructions, 19 November 2026**. Status **NO-GO** until isolated full PostgreSQL/Storage restore, verified private files, frozen writes, and a separately approved change. No live data/role/Storage change was made by this PR.

## Purpose and pinned resources
Source Supabase **`krwoiucqfcijmihnrlem`** (`public` app-state / `klarin-private-attachments`). Destination is one of the two permanent BASEs: **`numlkqppirrxfwdhazja`** (`csb_klarin` app-state and dedicated private `gpro-csb-private-attachments` bucket). **Never** write claim attachments into `gpp_stock` or legacy `public` in the target.

Only one workspace `default` is supported. State + realtime + attachment metadata are 3 separate tenant tables; actual Storage objects are separately stored binary blobs, not rows.

## Verified live inventory (read-only, 19 Nov; not a frozen checkpoint)
| | Source legacy | Tenant target |
|---|---:|---:|
| State version, realtime version | 40 / 40 | 38 / 38 |
| JSON state top-level keys | 21 | 21 |
| `monitoringKlaim` | 4 | 0 |
| `uploadBatches` | 2 | 1 |
| `auditLogs` | 39 | 37 |
| Claim metadata | 6 | 0 |
| Storage objects | 6 | 0 |
| Total object bytes | 2,918,989 | 0 |
| SHA-256 `state::text` | `ed2484691d19350379127452d496a6ddbcaf57ba371fabf8c75937154eeb698c` | `2da0b30b5641558ddc39098e548e3b1f563233f4e6398ffcd2608a89e5726303` |

**Important:** reexecute the two reviewed aggregate-only SQL queries **after formally freezing writes** to create the **new** snapshot values:
- `ops/sql/csb_klarin_source_locked_snapshot_READ_ONLY.sql`
- `ops/sql/csb_klarin_target_locked_snapshot_READ_ONLY.sql`

Their filenames include "locked" to signify their **intended approval checkpoint**; the queries themselves **do not acquire any lock or freeze**. Cross-project source/target consistency cannot be assumed from two independent read-only SQL queries while writes continue. Do not use the older example SHA-256 values to authorize a live transfer.

## Real physical Storage must be staged first
1. Verify full **7-project** PostgreSQL roles/schema/data and Storage-object export and an **actual successful restore** to an existing isolated environment, with sign-offs and rollback proof. Do not buy a new project or try to restore onto either active BASE.
2. Freeze all source claim writes, audit/event changes, uploads and administrative actions; record the frozen checkpoint and latest source + target aggregate SQL and versions.
3. Using an authorized server-side Storage client with private, operator-held credentials, export **every byte** from six original source objects. Preserve each `storage_path`, `owner_type=klaim`, `owner_id`, attachment ID, MIME, and sizes. Never copy just `storage.objects` rows.
4. Stage each exact file in `gpro-csb-private-attachments` bucket on **target BASE**, keeping its original private object key and content-type, **without overwriting target-only files**. Record upload/readback success. The source bucket remains untouched.
5. Independently download/read back the target objects into a separate private local root. Compute a genuine SHA-256 of original source bytes **and target bytes**. Verify target authorized CSB session can download, but unauthorized GPP/BBM and browser `anon` cannot. Store all data and manifests in an encrypted, access-restricted operator workstation; never GitHub Actions artifacts or chat.

The local JSON manifest is a private array of six records. Each needs `id`, `owner_type`, `owner_id`, `file_name`, `mime_type`, `size_bytes`, `storage_path`, and **an independently obtained `expected_sha256` of the original object bytes**. `data_base64`, claim content, user credentials and JWTs do **not** belong in the manifest. Both separate local trees must preserve the relative `storage_path`.

## Guarded script and preconditions
`ops/scripts/csb_klarin_state_transfer_guarded.py` requires Python 3.10+, `psycopg` v3 and the two sibling offline tools `csb_klarin_claim_delta_plan.py` and `csb_klarin_storage_byte_audit.py`. It has no built-in secret or public Storage transfer. Provide **operator-only** DSNs from protected environment variables:
- `GPRO_CSB_KLARIN_SOURCE_DSN` — original Klarin project; only exact pinned project `postgres` operator account accepted.
- `GPRO_CSB_KLARIN_TARGET_DSN` — target Klarin BASE; only exact pinned project `postgres` operator account accepted.

Keep the credentials out of terminal history, log files, CI, source code, screenshots and chat.

**Default read-only rehearsal**: from the repository root on the approved private machine, with operator environment configured:
```bash
python3 ops/scripts/csb_klarin_state_transfer_guarded.py
```
This reads state, versions, attachment metadata, and checks business ID conflicts and tenant RLS/grants. It **does not** transfer file bytes or write target data.

**Operator-controlled apply is a separate approved change, not run by this PR**. After ALL checks and source freeze, and **only** with the freshly computed snapshot values, the authorized operator may follow this illustrative contract (placeholders must be independently verified, not guessed):
```bash
python3 ops/scripts/csb_klarin_state_transfer_guarded.py \
  --apply \
  --approved-change-ref '<approved change ID>' \
  --verified-restore-ref '<successful restore evidence ID>' \
  --confirm-frozen-writes \
  --source-version <frozen source version> \
  --target-version <frozen target version> \
  --source-sha256 '<frozen source JSONB sha256>' \
  --target-sha256 '<frozen target JSONB sha256>' \
  --expected-attachments <frozen file count> \
  --expected-total-bytes <frozen total bytes> \
  --manifest /secure/private-csb-attachments.json \
  --source-root /secure/csb-original \
  --target-root /secure/csb-target-readback
```

## What the script enforces
- Source PostgreSQL transaction **REPEATABLE READ READ ONLY**; target **SERIALIZABLE** and table locks, no direct public consumer call.
- Target `csb_klarin` three tables must retain RLS, no `anon`/`authenticated`/`gpro_gpp_stock` CRUD; every server-role SELECT/INSERT/UPDATE/DELETE permission is verified **individually**.
- Source and target state versions, exact `state::text` SHA-256 and realtime signal versions must match the **approved frozen snapshots**.
- All 21 state top-level keys must match except three approved delta arrays; each existing target ID must exist and have identical content in source, with no target-only entries or business ID conflicts. Existing values are preserved, new entries inserted by stable ID and three arrays reordered to match source exactly.
- All six source and staged target Storage metadata objects must have identical **object names and sizes**, and must correspond exactly to attachment metadata; there are no extra or missing target objects. **Every source and target file byte** in the operator's separate readback trees must match independently verified source SHA-256.
- Attachments are inserted by exact ID only if missing; existing target IDs must have identical metadata. No `ON CONFLICT DO UPDATE`, no overwrite, no deletion or UUID regeneration.
- State and realtime versions are updated with optimistic **version+state compare-and-swap** in a single target transaction. If another writer modifies state or a required file is missing, the database changes roll back.
- Successful metadata/state transfer does **not** prove app login, account lock, posting, reversal, deletion, or private Storage E2E. A separate signed QA and production cutover approval are mandatory.

## Post-apply proofs and rollback
Re-run aggregate-only source and target SQL. Confirm both now show the exact same JSON state SHA-256, state version and realtime version, and matching **six objects / 2,918,989 bytes** after the approved frozen checkpoint. Then test authenticated claim create/edit/retur and private PDF/XLSX preview, unknown owner denials, cross-tenant denial, and app impact. Keep original source project active, all physical file exports encrypted, and the full rollback checkpoint available. Cross-project PostgreSQL and Storage transfers are not globally atomic: if DB changes fail, staged files may remain and require an audited cleanup decision. **Do not delete any of the five legacy projects without a new explicit owner authorization.**

**Current decision: NO-GO**. The target still has **zero** of the six physical objects and there is no demonstrated full PostgreSQL + Storage restore. The script intentionally fails in this situation.
