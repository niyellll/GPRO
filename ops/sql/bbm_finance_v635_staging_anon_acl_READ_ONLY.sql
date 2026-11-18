-- BBM Finance Public V635 staging ACL audit: READ ONLY.
-- Target PROJECT ONLY: fdhqidjltlihzdcbqfrd
-- This reports grants + RLS policy counts without revealing any migration_key.
-- A role with anon INSERT plus a matching policy is not proper user authorization.
-- Never treat presence of RLS alone as a zero-risk guarantee.
WITH stage(table_name) AS (
 VALUES
    ('bbm_v635_stage_accounts'),
    ('bbm_v635_stage_audit_logs'),
    ('bbm_v635_stage_bbm_accounting_controls_v333'),
    ('bbm_v635_stage_customers'),
    ('bbm_v635_stage_excel_data'),
    ('bbm_v635_stage_journal_details'),
    ('bbm_v635_stage_journals'),
    ('bbm_v635_stage_rekening_koran'),
    ('bbm_v635_stage_users')
), rows AS (
 SELECT s.table_name,
        c.oid IS NOT NULL AS exists,
        COALESCE(c.relrowsecurity,false) AS rls_enabled,
        CASE WHEN c.oid IS NULL THEN false
             ELSE has_table_privilege('anon',c.oid,'INSERT') END AS anon_insert,
        CASE WHEN c.oid IS NULL THEN false
             ELSE has_table_privilege('anon',c.oid,'SELECT') END AS anon_select,
        CASE WHEN c.oid IS NULL THEN false
             ELSE has_table_privilege('authenticated',c.oid,'INSERT') END AS authenticated_insert,
        (SELECT count(*)::int
           FROM pg_policies p
          WHERE p.schemaname='public'
            AND p.tablename=s.table_name
            AND p.cmd IN('INSERT','ALL')
            AND 'anon'=ANY(p.roles)) AS anon_insert_policy_count
 FROM stage s
 LEFT JOIN pg_class c ON c.oid=to_regclass(format('%I.%I','public',s.table_name))
)
SELECT table_name,exists,rls_enabled,anon_insert,anon_select,authenticated_insert,
       anon_insert_policy_count,
       (exists AND rls_enabled AND anon_insert AND anon_insert_policy_count>0) AS anon_insert_surface_exposed
 FROM rows ORDER BY table_name;
