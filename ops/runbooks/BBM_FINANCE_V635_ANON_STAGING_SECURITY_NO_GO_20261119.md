# BBM Finance V635 legacy staging — anonymous INSERT security hardening
**LIVE catalog checked 19 November 2026, Asia/Jakarta.** This is a **NO-GO review**; no production table, policy, grant, or data was changed.

## Verified facts, not an exploitation claim
Project `bbm-finance` `fdhqidjltlihzdcbqfrd` contains **nine legacy `public.bbm_v635_stage_*` tables** that are all **empty** at the read-only check. Every one has:
- RLS **enabled**.
- `anon` role with a **direct `INSERT` GRANT**, but no `SELECT` GRANT.
- One `INSERT` RLS policy scoped to `anon`, conditioned on a fixed `migration_key` value. This grants a potential write path to callers who can satisfy the condition, not identity-based permission. The secret-like value is deliberately **NOT copied to this public report**.
- `authenticated` does **not** have an INSERT GRANT to these staging tables.
- `service_role` preserves full server-side access.

These findings are from `pg_class`, `pg_policies`, `information_schema.role_table_grants`, `has_table_privilege()`, and actual read-only `COUNT(*)` on all nine tables. No external exploit or public Data API reachability test was performed. In Supabase, the Data API also depends on schema exposure, server settings, GRANTs and RLS together. RLS policy presence alone does not prove an active external route.

### Why caution matters
Fixed-value RLS validation is not a substitute for authenticated identity, and public staging tables can become an unintended injection surface if the Data API exposes them and the fixed value becomes known. On the other hand, removing a grant while an old migration/import client still depends on it could cause failed writes. Existing rows are zero now, but operator must still verify no pending migration job, old client, maintenance process or scheduled import depends on this grant.

## Prepared artifacts, NOT executed
- `ops/sql/bbm_finance_v635_staging_anon_acl_READ_ONLY.sql` — verified LIVE: **9/9 anon INSERT privilege=true, 9/9 anon INSERT policy present, RLS=true**, no anon SELECT.
- `ops/sql/bbm_finance_v635_stage_revoke_anon_REVIEW_ONLY.sql` — transaction-scoped proposal, **not run**. Preflight checks exact nine table names, table existence, RLS, original grants, server access and table emptiness, aborts on drift, revokes **only anon INSERT**, then asserts no anon SELECT/INSERT remains while server access is preserved. Does not drop tables, clear data, alter policies, grant any extra privilege or include the fixed key.
- `ops/tests/test_bbm_finance_staging_acl.py` — seven offline tests for scope, safety, RLS/ACL audit, no secret values, no DML or destructive DDL.
- The locked production baseline and tenant schemas are unaffected by this **review-only** work.

## Formal approval gates for any future change
1. Verify the precise Data API exposure and intended old V635 migration use, confirm no active `anon` ingestion or scheduled external clients, and record the last maintenance use. Do not test by inserting fake records in production.
2. Capture a fresh source/target database snapshot and **prove restore** of Finance database plus Storage to an isolated existing environment, not a live BASE.
3. Review the grant and RLS policy together, including any future `GRANT` automation that could inadvertently re-enable the policy, and decide separately whether the stale policy should eventually be retired.
4. Agree on rollback (securely regrant only if required by a reviewed approved legacy migration; no public migration key in logs), operator, change window and incident notifications.
5. Only after explicit approval apply the reviewed script to the **correct project**; check the post-condition with the read-only audit and verify BBM Finance functionality, staging import alternatives, journals and tenant isolation E2E.
6. Leave the five legacy databases active; this is security hardening, not authorization for wider migration/cutover.

**NO-GO now:** not applied, preview testing and full restore not yet done.

Reference: [Supabase Securing your API](https://supabase.com/docs/guides/api/securing-your-api), [Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security).
