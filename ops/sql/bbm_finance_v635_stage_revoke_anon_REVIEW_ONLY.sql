-- BBM FINANCE security hardening, REVIEW ONLY, NOT APPLIED.
-- Expected target: fdhqidjltlihzdcbqfrd (bbm-finance), schema public.
--
-- AUTHORIZED OPERATOR MUST CONFIRM NO ACTIVE USE, COMPLETED FULL BACKUP +
-- SUCCESSFUL RESTORE DRILL, APPROVED CUTOVER PLAN AND OWNER CHANGE APPROVAL.
-- These 9 legacy V635 staging tables have 0 rows in a live read-only audit
-- and have direct anon INSERT grants plus RLS INSERT policies with a fixed
-- migration-key condition. A fixed value is not user authorization.
--
-- This script REVOKES only anon INSERT. It preserves:
--  * table definitions, RLS policies, all source/data rows;
--  * all server-side service_role grants;
--  * the existing public/tenant database schemas and protected baseline.
--
-- This script has NOT been executed on production. Any source write after
-- preflight, schema drift, or required privilege change MUST be investigated.
-- DO NOT remove migration policies or drop tables without a separate review.
--
-- No real migration key values or customer records are embedded here.
BEGIN;
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '20s';

-- Acquire explicit concurrent-writer exclusion BEFORE checking for zero rows.
-- If an active migration is writing, lock_timeout will abort the change.
-- Locks remain held through preflight, REVOKE and postflight until COMMIT.
LOCK TABLE
  public.bbm_v635_stage_accounts,
  public.bbm_v635_stage_audit_logs,
  public.bbm_v635_stage_bbm_accounting_controls_v333,
  public.bbm_v635_stage_customers,
  public.bbm_v635_stage_excel_data,
  public.bbm_v635_stage_journal_details,
  public.bbm_v635_stage_journals,
  public.bbm_v635_stage_rekening_koran,
  public.bbm_v635_stage_users
IN SHARE ROW EXCLUSIVE MODE;

DO $preflight$
DECLARE
  stage_name text;
  rows_found bigint;
  relation_oid oid;
  stage_names text[] := ARRAY[
    'bbm_v635_stage_accounts',
    'bbm_v635_stage_audit_logs',
    'bbm_v635_stage_bbm_accounting_controls_v333',
    'bbm_v635_stage_customers',
    'bbm_v635_stage_excel_data',
    'bbm_v635_stage_journal_details',
    'bbm_v635_stage_journals',
    'bbm_v635_stage_rekening_koran',
    'bbm_v635_stage_users'
  ];
BEGIN
  IF (SELECT count(DISTINCT x) FROM unnest(stage_names) AS x) <> 9 THEN
    RAISE EXCEPTION 'NO-GO: staging inventory is incomplete or duplicated';
  END IF;
  FOREACH stage_name IN ARRAY stage_names LOOP
    relation_oid := to_regclass(format('%I.%I', 'public', stage_name));
    IF relation_oid IS NULL THEN
      RAISE EXCEPTION 'NO-GO: expected staging table missing';
    END IF;
    IF NOT (SELECT c.relkind='r' AND c.relrowsecurity
            FROM pg_class c WHERE c.oid=relation_oid) THEN
      RAISE EXCEPTION 'NO-GO: staging table relkind or RLS differs from audit';
    END IF;
    IF NOT has_table_privilege('anon', relation_oid, 'INSERT')
       OR has_table_privilege('anon', relation_oid, 'SELECT') THEN
      RAISE EXCEPTION 'NO-GO: staging table anon privilege inventory changed';
    END IF;
    IF NOT has_table_privilege('service_role', relation_oid, 'SELECT,INSERT,UPDATE,DELETE') THEN
      RAISE EXCEPTION 'NO-GO: service role permissions differ from inventory';
    END IF;
    EXECUTE format('SELECT count(*) FROM %I.%I', 'public', stage_name) INTO rows_found;
    IF rows_found <> 0 THEN
      RAISE EXCEPTION 'NO-GO: staging table contains records, investigate before privilege changes';
    END IF;
  END LOOP;
END
$preflight$;

REVOKE INSERT ON TABLE
  public.bbm_v635_stage_accounts,
  public.bbm_v635_stage_audit_logs,
  public.bbm_v635_stage_bbm_accounting_controls_v333,
  public.bbm_v635_stage_customers,
  public.bbm_v635_stage_excel_data,
  public.bbm_v635_stage_journal_details,
  public.bbm_v635_stage_journals,
  public.bbm_v635_stage_rekening_koran,
  public.bbm_v635_stage_users
FROM anon;

DO $verify$
DECLARE
  stage_name text;
  relation_oid oid;
BEGIN
  FOREACH stage_name IN ARRAY ARRAY[
    'bbm_v635_stage_accounts',
    'bbm_v635_stage_audit_logs',
    'bbm_v635_stage_bbm_accounting_controls_v333',
    'bbm_v635_stage_customers',
    'bbm_v635_stage_excel_data',
    'bbm_v635_stage_journal_details',
    'bbm_v635_stage_journals',
    'bbm_v635_stage_rekening_koran',
    'bbm_v635_stage_users'
  ] LOOP
    relation_oid := to_regclass(format('%I.%I', 'public', stage_name));
    IF relation_oid IS NULL OR
       has_table_privilege('anon',relation_oid,'INSERT') OR
       has_table_privilege('anon',relation_oid,'SELECT') OR
       NOT has_table_privilege('service_role',relation_oid,'SELECT,INSERT,UPDATE,DELETE') THEN
      RAISE EXCEPTION 'NO-GO: post-revoke privileges invalid; rollback';
    END IF;
  END LOOP;
END
$verify$;
COMMIT;
