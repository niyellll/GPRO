-- GPRO TWO-BASE ${label} live tenant-role catalog acceptance test: READ ONLY.
-- Target Supabase PROJECT: fdhqidjltlihzdcbqfrd
-- No password/hash value is returned. This cannot prove actual network LOGIN.
-- This is a privilege matrix, NOT authenticated application E2E.
WITH tenant(login_role, expected_schema) AS (
 VALUES
 ('gpro_csb_finance','csb_finance'),
 ('gpro_gpp_pusat','gpp_piutang'),
 ('gpro_gpp_cabang','gpp_finance_cabang')
), tbl AS (
 SELECT c.oid, n.nspname, c.relrowsecurity
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE n.nspname IN('public', 'csb_finance', 'gpp_piutang', 'gpp_finance_cabang') AND c.relkind IN ('r','p')
)
SELECT t.login_role, t.expected_schema,
  r.rolcanlogin AS login_flag,
  (a.rolpassword IS NOT NULL) AS credential_configured,
  has_schema_privilege(t.login_role,t.expected_schema,'USAGE') AS expected_schema_usage,
  count(*) FILTER(WHERE tbl.nspname=t.expected_schema) AS expected_tables,
  count(*) FILTER(WHERE tbl.nspname=t.expected_schema AND tbl.relrowsecurity) AS expected_tables_with_rls,
  count(*) FILTER(WHERE tbl.nspname=t.expected_schema AND has_table_privilege(t.login_role,tbl.oid,'SELECT')) AS expected_tables_selectable,
  count(*) FILTER(WHERE tbl.nspname=t.expected_schema AND has_table_privilege(t.login_role,tbl.oid,'INSERT')) AS expected_tables_insertable,
  count(*) FILTER(WHERE tbl.nspname=t.expected_schema AND has_table_privilege(t.login_role,tbl.oid,'UPDATE')) AS expected_tables_updateable,
  count(*) FILTER(WHERE tbl.nspname=t.expected_schema AND has_table_privilege(t.login_role,tbl.oid,'DELETE')) AS expected_tables_deletable,
  count(*) FILTER(WHERE tbl.nspname<>t.expected_schema AND has_table_privilege(t.login_role,tbl.oid,'SELECT')) AS cross_schema_selectable,
  count(*) FILTER(WHERE tbl.nspname<>t.expected_schema AND has_table_privilege(t.login_role,tbl.oid,'INSERT')) AS cross_schema_insertable,
  (SELECT count(*) FROM pg_namespace n
   WHERE n.nspname IN('public', 'csb_finance', 'gpp_piutang', 'gpp_finance_cabang') AND n.nspname<>t.expected_schema
     AND has_schema_privilege(t.login_role,n.oid,'USAGE')) AS other_schema_usage_count
FROM tenant t
JOIN pg_roles r ON r.rolname=t.login_role
JOIN pg_authid a ON a.rolname=t.login_role
CROSS JOIN tbl
GROUP BY t.login_role,t.expected_schema,r.rolcanlogin,a.rolpassword
ORDER BY t.login_role;
