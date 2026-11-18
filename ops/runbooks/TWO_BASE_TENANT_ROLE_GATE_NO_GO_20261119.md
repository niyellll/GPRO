# Two BASEs — tenant database role and restricted routine matrix (NO-GO)
**Live read-only catalog checks completed 19 Nov 2026 (Asia/Jakarta).** These results are not an authenticated network login or application E2E.

## Target Finance: `fdhqidjltlihzdcbqfrd`
| Dedicated login role | Allowed schema | Tables | RLS on | Role SELECT | Role INSERT / UPDATE / DELETE | Cross-schema table SELECT | Password configured |
|---|---|---:|---:|---:|---:|---:|---|
| `gpro_csb_finance` | `csb_finance` | 36 | 36 | 36 | 0 / 0 / 0 | 0 | NO |
| `gpro_gpp_pusat` | `gpp_piutang` | 23 | 23 | 23 | 0 / 0 / 0 | 0 | NO |
| `gpro_gpp_cabang` | `gpp_finance_cabang` | 23 | 23 | 23 | 0 / 0 / 0 | 0 | NO |

All three lack schema USAGE on other selected Finance schemas, including `public`. They have no actual callable `SECURITY DEFINER` routines in the checked four schemas. `public` owns 62 SECURITY DEFINER functions; none can be reached by these tenant roles with their current schema/function permissions.

## Target Klarin: `numlkqppirrxfwdhazja`
| Dedicated login role | Allowed data schema | Tables | RLS on | Role SELECT | Role INSERT / UPDATE / DELETE | Cross-schema table SELECT | Password configured |
|---|---|---:|---:|---:|---:|---:|---|
| `gpro_csb_klarin` | `csb_klarin` | 7 | 7 | 7 | 0 / 0 / 0 | 0 | NO |
| `gpro_gpp_stock` | `gpp_stock` | 6 | 6 | 6 | 0 / 0 / 0 | 0 | NO |

Both Klarin roles have schema USAGE on legacy `public`, **but no `public` table SELECT/INSERT privileges** were detected for them. This is not equivalent to zero access to ALL object types; routine execution was therefore audited separately. No callable `SECURITY DEFINER` function was found for them in checked schemas. All dedicated tenant schemas have RLS enabled on every catalogued table.

### Separate public Klarin realtime notice
The legacy `public.klarin_realtime_signal` table has RLS enabled, and both `anon` and `authenticated` have SELECT access through a `USING (true)` policy. The table columns are `workspace_key`, `version` and `updated_at`, not claim content. It may be intentional polling/realtime compatibility. **Do not revoke without auditing client usage and E2E**, as doing so may break notifications. The separate CSB and GPP tenant signal tables have no browser table grants.

## Important implications
- **Database-privilege isolation currently looks correct for the 5 read-only roles** in the checked table/function schemas. This is catalog evidence only; cannot prove connection authentication, browser access through PostgREST, private file rights, SQL function bodies, or server gateway authorization.
- **All 5 dedicated LOGIN roles have no saved login password.** Preview routing must remain fail-closed. Do not paste secrets into GitHub or create credentials without an approved change/secret rotation plan.
- **There is no DML role attached to these tenant logins.** GPP Finance Next.js bank/journal routes need INSERT/UPDATE/DELETE and have legacy runtime CREATE/ALTER table paths. Enabling a routing flag while relying on read-only roles cannot be described as a working transaction workflow. Fix approved server-side write authority with strict verified sessions, allowlisted workspace and table/action authorization and auditable operations. **Do NOT grant global DML to the five read-only roles** or expose `service_role` to browsers.
- `service_role` can access multiple Finance/Klarin tenant schemas and must only be used in an authenticated, audited, server-side gateway with explicit tenant mapping. Its broad privileges do NOT supply tenant isolation by themselves.
- Independent public Finance anonymous staging issue: nine `public.bbm_v635_stage_*` tables have `anon INSERT` and fixed-value RLS policies, but are empty at the live check. [Separate staged review](BBM_FINANCE_V635_ANON_STAGING_SECURITY_NO_GO_20261119.md) provides a non-applied revoke script.

## Reproducible queries (READ ONLY)
- `ops/sql/two_base_finance_tenant_role_gate_READ_ONLY.sql` — executed successfully against Finance.
- `ops/sql/two_base_klarin_tenant_role_gate_READ_ONLY.sql` — executed successfully against Klarin.
These queries report **only credential presence booleans, never password hashes or secret values**. Data correction is NOT included.

## Remaining release gates
Complete 7-project full PostgreSQL+Storage export AND actual isolated restore; tenant LOGIN secret provisioning in a protected environment; authenticated read/write and cross-tenant denial tests; verify UI/read/write/approve/journal/upload paths; finish frozen-source delta sync and real Storage byte checks; complete Preview build without quota bypass, then approved controlled cutover. **Do not delete old projects.**

**Status: NO-GO.**
