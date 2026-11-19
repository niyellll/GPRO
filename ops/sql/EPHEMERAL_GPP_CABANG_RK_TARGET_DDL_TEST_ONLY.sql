-- EPHEMERAL PostgreSQL 17 TEST ONLY, NEVER RUN ON LIVE SUPABASE.
-- Requires EPHEMERAL_GPP_RK_TARGET_DDL_TEST_ONLY.sql to have run first:
-- it creates synthetic gpro_gpp_pusat, gpro_gpp_cabang, service_role, etc.
-- Confirm Cabang schema, RLS/GRANT inheritance, private writes and
-- explicit prohibition of cross-tenant (Pusat, anon, CSB) SELECT.
\set ON_ERROR_STOP on

BEGIN;
CREATE ROLE gpro_gpp_finance_cabang_ro_v1 NOLOGIN;
CREATE SCHEMA gpp_finance_cabang;
REVOKE ALL ON SCHEMA gpp_finance_cabang FROM PUBLIC;
GRANT USAGE ON SCHEMA gpp_finance_cabang
 TO gpro_gpp_finance_cabang_ro_v1,service_role;
GRANT gpro_gpp_finance_cabang_ro_v1 TO gpro_gpp_cabang WITH INHERIT TRUE;
COMMIT;

-- Execute the EXACT review-only Cabang target migration, on disposable PG.
\ir gpp_finance_cabang_rekening_koran_v439_create_REVIEW_ONLY.sql

DO $verify$
DECLARE
  protected_count integer;
BEGIN
  SELECT count(*) INTO protected_count FROM pg_class c
   JOIN pg_namespace n ON n.oid=c.relnamespace
   WHERE n.nspname='gpp_finance_cabang' AND
     c.relname IN ('rekening_koran_working_lines_v439','rekening_koran_period_meta_v543')
     AND c.relrowsecurity;
  IF protected_count<>2 THEN RAISE EXCEPTION
   'NO-GO: Cabang RK and period schema are not both RLS protected'; END IF;
  IF NOT has_table_privilege('gpro_gpp_cabang',
       'gpp_finance_cabang.rekening_koran_working_lines_v439','SELECT')
     OR NOT has_table_privilege('gpro_gpp_cabang',
       'gpp_finance_cabang.rekening_koran_period_meta_v543','SELECT')
     OR has_table_privilege('gpro_gpp_pusat',
       'gpp_finance_cabang.rekening_koran_working_lines_v439','SELECT')
     OR has_table_privilege('anon',
       'gpp_finance_cabang.rekening_koran_period_meta_v543','SELECT')
     OR has_table_privilege('gpro_gpp_cabang',
       'gpp_finance_cabang.rekening_koran_working_lines_v439','INSERT')
  THEN RAISE EXCEPTION 'NO-GO: Cabang tenant role security does not match expected ACL';
  END IF;
END
$verify$;

SET ROLE service_role;
INSERT INTO gpp_finance_cabang.rekening_koran_working_lines_v439(
 id,bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo,
 source_order,is_active
) VALUES (md5('cabang-test')::uuid,'SYNTH-CABANG','2026-10-01',
 'CABANG-RK','SYNTHETIC-CABANG',0,25,125,1,true);
INSERT INTO gpp_finance_cabang.rekening_koran_period_meta_v543 (
 bank_account_code,period_key,opening_balance,closing_balance,source_type
) VALUES ('SYNTH-CABANG','2026-10',100,125,'TEST');
RESET ROLE;

SET ROLE gpro_gpp_cabang;
DO $read$
BEGIN
  IF (SELECT count(*) FROM gpp_finance_cabang.rekening_koran_working_lines_v439)<>1
    OR (SELECT count(*) FROM gpp_finance_cabang.rekening_koran_period_meta_v543)<>1
  THEN RAISE EXCEPTION 'NO-GO: Cabang reader could not see its own tenant data';END IF;
END
$read$;
DO $blocked_write$
BEGIN
  BEGIN
    INSERT INTO gpp_finance_cabang.rekening_koran_period_meta_v543
    (bank_account_code,period_key) VALUES ('BAD','2026-11');
    RAISE EXCEPTION 'NO-GO: Cabang read-only role unexpectedly wrote';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END
$blocked_write$;
RESET ROLE;

SET ROLE gpro_gpp_pusat;
DO $cross_denied$
BEGIN
  BEGIN
    PERFORM 1 FROM gpp_finance_cabang.rekening_koran_working_lines_v439;
    RAISE EXCEPTION 'NO-GO: Pusat unexpectedly read Cabang bank lines';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END
$cross_denied$;
RESET ROLE;

SET ROLE anon;
DO $browser_denied$
BEGIN
  BEGIN
    PERFORM 1 FROM gpp_finance_cabang.rekening_koran_period_meta_v543;
    RAISE EXCEPTION 'NO-GO: browser anon unexpectedly read Cabang periods';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END
$browser_denied$;
RESET ROLE;

SELECT 'GPP_CABANG_EPHEMERAL_SCHEMA_DDL_PASS' AS result;
