-- EPHEMERAL PostgreSQL 17 TEST ONLY. NEVER RUN ON LIVE SUPABASE.
-- Prepare synthetic roles/schema and then execute EXACT existing REVIEW_ONLY
-- proposed target DDL. This validates inherited RLS, no cross-tenant SELECT,
-- read-only GPP login role and scoped service-role DML.
\set ON_ERROR_STOP on

BEGIN;
CREATE ROLE gpro_gpp_piutang_ro_v1 NOLOGIN;
CREATE ROLE gpro_gpp_pusat LOGIN;
CREATE ROLE gpro_gpp_cabang LOGIN;
CREATE ROLE gpro_csb_finance LOGIN;
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;
CREATE SCHEMA gpp_piutang;
REVOKE ALL ON SCHEMA gpp_piutang FROM PUBLIC;
GRANT USAGE ON SCHEMA gpp_piutang TO gpro_gpp_piutang_ro_v1, service_role;
GRANT gpro_gpp_piutang_ro_v1 TO gpro_gpp_pusat WITH INHERIT TRUE;
COMMIT;

-- Run the reviewed production DDL in an ISOLATED PG17 container, not in a BASE.
\ir gpp_piutang_rekening_koran_v439_create_REVIEW_ONLY.sql

DO $validate$
DECLARE
  tables_count int;
  policy_count int;
BEGIN
  SELECT count(*) INTO tables_count
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='gpp_piutang' AND c.relname IN (
    'rekening_koran_working_lines_v439','rekening_koran_period_meta_v543'
  ) AND c.relrowsecurity;
  IF tables_count<>2 THEN
    RAISE EXCEPTION 'NO-GO: schema did not create both protected GPP RK tables';
  END IF;
  SELECT count(*) INTO policy_count FROM pg_policies
  WHERE schemaname='gpp_piutang' AND tablename IN (
    'rekening_koran_working_lines_v439','rekening_koran_period_meta_v543')
    AND 'gpro_gpp_piutang_ro_v1'=ANY(roles) AND cmd='SELECT';
  IF policy_count<>2 THEN
    RAISE EXCEPTION 'NO-GO: RLS did not provide dedicated reader policies';
  END IF;
  IF NOT has_schema_privilege('gpro_gpp_pusat','gpp_piutang','USAGE') OR
      NOT has_table_privilege('gpro_gpp_pusat',
        'gpp_piutang.rekening_koran_working_lines_v439','SELECT') OR
      has_table_privilege('gpro_gpp_pusat',
        'gpp_piutang.rekening_koran_working_lines_v439','INSERT') OR
      has_table_privilege('gpro_gpp_cabang',
        'gpp_piutang.rekening_koran_working_lines_v439','SELECT') OR
      has_table_privilege('anon',
        'gpp_piutang.rekening_koran_period_meta_v543','SELECT') THEN
    RAISE EXCEPTION 'NO-GO: roles or cross-tenant grants do not meet contract';
  END IF;
END
$validate$;

-- Write fixtures through the trusted server-only role, never GPP reader.
SET ROLE service_role;
INSERT INTO gpp_piutang.rekening_koran_working_lines_v439 (
  id,bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo,
  source_order,is_active
) VALUES
 (md5('historic')::uuid,'SYNTH-BANK','2026-10-01','R1','SYNTHETIC',120,0,500,1,false),
 (md5('current')::uuid,'SYNTH-BANK','2026-10-01','R1','SYNTHETIC',120,0,500,1,true);
INSERT INTO gpp_piutang.rekening_koran_period_meta_v543 (
  bank_account_code,period_key,opening_balance,closing_balance,source_type
) VALUES ('SYNTH-BANK','2026-10',380,500,'TEST');
RESET ROLE;

-- Inherited read-only role can SELECT, including RLS select policy.
SET ROLE gpro_gpp_pusat;
DO $can_read$
DECLARE rows_all int; rows_active int;
BEGIN
  SELECT count(*) INTO rows_all FROM gpp_piutang.rekening_koran_working_lines_v439;
  SELECT count(*) INTO rows_active
    FROM gpp_piutang.rekening_koran_working_lines_v439
    WHERE coalesce(is_active,true);
  IF rows_all<>2 OR rows_active<>1
    OR (SELECT count(*) FROM gpp_piutang.rekening_koran_period_meta_v543)<>1 THEN
    RAISE EXCEPTION 'NO-GO: inherited GPP reader policy or active/archive filtering wrong';
  END IF;
END
$can_read$;
DO $cannot_write$
BEGIN
  BEGIN
    INSERT INTO gpp_piutang.rekening_koran_period_meta_v543
      (bank_account_code,period_key)
    VALUES ('BYPASS','2026-11');
    RAISE EXCEPTION 'NO-GO: GPP reader unexpectedly inserted period metadata';
  EXCEPTION WHEN insufficient_privilege THEN
    NULL;
  END;
END
$cannot_write$;
RESET ROLE;

-- Cabang and browser roles have no tenant schema/table access.
SET ROLE gpro_gpp_cabang;
DO $cabang_denied$
BEGIN
  BEGIN
    PERFORM 1 FROM gpp_piutang.rekening_koran_working_lines_v439;
    RAISE EXCEPTION 'NO-GO: Cabang could read Pusat RK';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END
$cabang_denied$;
RESET ROLE;
SET ROLE anon;
DO $anon_denied$
BEGIN
  BEGIN
    PERFORM 1 FROM gpp_piutang.rekening_koran_period_meta_v543;
    RAISE EXCEPTION 'NO-GO: anon could read Pusat metadata';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END
$anon_denied$;
RESET ROLE;

SELECT 'GPP_RK_EPHEMERAL_TARGET_SCHEMA_DDL_PASS' AS result;
