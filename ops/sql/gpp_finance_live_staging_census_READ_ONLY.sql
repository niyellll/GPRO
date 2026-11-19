-- LIVE FINANCE BASE staging reconciliation: READ ONLY, NO RAW CUSTOMER DATA.
-- Project: fdhqidjltlihzdcbqfrd (bbm-finance), tenant: gpp_piutang.
-- Initial full-history copy from legacy vmpurwykfzcmculnnjfw on 19 Nov 2026.
-- 94 UUID records include 47 active and 47 archived historical versions.
-- Recompute against source AFTER approved write freeze for final cutover;
-- this read-only query cannot prove live source remains unchanged.
WITH rk AS (
  SELECT t.id,t.is_active,t.debet,t.kredit,
    (to_jsonb(t)-'matched_journal_no'-'matched_source'-'attachment_note')::text AS source_shape
  FROM gpp_piutang.rekening_koran_working_lines_v439 AS t
), census AS (
  SELECT count(*)::bigint AS rows_all,
    count(DISTINCT id)::bigint AS distinct_uuid,
    count(*) FILTER(WHERE coalesce(is_active,true))::bigint AS rows_active,
    count(*) FILTER(WHERE is_active IS FALSE)::bigint AS rows_archived,
    count(*) FILTER(WHERE is_active IS NULL)::bigint AS rows_null_status,
    coalesce(sum(debet) FILTER(WHERE coalesce(is_active,true)),0) AS debit_active,
    coalesce(sum(kredit) FILTER(WHERE coalesce(is_active,true)),0) AS credit_active,
    encode(sha256(convert_to(
      coalesce(string_agg(source_shape,E'\n' ORDER BY id),''),
      'UTF8')),'hex') AS source_column_sha256
  FROM rk
), roles AS (
  SELECT 'gpp_piutang'::text AS tenant, 'gpro_gpp_pusat'::text AS own_role,
    'gpro_gpp_cabang'::text AS other_role
  UNION ALL
  SELECT 'gpp_finance_cabang', 'gpro_gpp_cabang','gpro_gpp_pusat'
)
SELECT c.*,
  (c.rows_all=94 AND c.rows_active=47 AND c.rows_archived=47
    AND c.rows_null_status=0 AND c.distinct_uuid=94
    AND c.source_column_sha256=
      'bbb37b90446aca2820d00dee0f028b846795e4223e1f01dec4ae38a18cdb543f')
    AS equals_original_19_nov_staging_snapshot,
  (SELECT count(*)::bigint FROM gpp_piutang.rekening_koran_period_meta_v543)
    AS pusat_period_meta_rows,
  (SELECT count(*)::bigint FROM gpp_finance_cabang.rekening_koran_working_lines_v439)
    AS cabang_rk_rows,
  (SELECT count(*)::bigint FROM gpp_finance_cabang.rekening_koran_period_meta_v543)
    AS cabang_period_meta_rows,
  (SELECT bool_and(p.relrowsecurity AND
    has_table_privilege(r.own_role,p.oid,'SELECT') AND
    NOT has_table_privilege(r.other_role,p.oid,'SELECT') AND
    NOT has_table_privilege('anon',p.oid,'SELECT') AND
    NOT has_table_privilege('authenticated',p.oid,'SELECT') AND
    NOT has_table_privilege(r.own_role,p.oid,'INSERT') AND
    has_table_privilege('service_role',p.oid,'SELECT') AND
    has_table_privilege('service_role',p.oid,'INSERT') AND
    has_table_privilege('service_role',p.oid,'UPDATE') AND
    has_table_privilege('service_role',p.oid,'DELETE'))
   FROM roles r
   JOIN pg_namespace n ON n.nspname=r.tenant
   JOIN pg_class p ON p.relnamespace=n.oid
    AND p.relname IN('rekening_koran_working_lines_v439','rekening_koran_period_meta_v543')
    AND p.relkind='r') AS all_four_tables_acl_pass
FROM census c;
