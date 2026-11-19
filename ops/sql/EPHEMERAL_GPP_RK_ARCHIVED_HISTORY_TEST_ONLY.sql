-- EPHEMERAL PG17 ONLY. NEVER RUN ON ANY REAL SUPABASE PROJECT.
-- Generates synthetic 47 inactive historical + 47 active versions (94 UUIDs),
-- verifies full-history transfer, unique effective-active business signatures,
-- safe financial totals, cross-tenant denial and rollback on double-active.
\set ON_ERROR_STOP on
BEGIN;
CREATE ROLE gpro_ci_rk_pusat NOLOGIN;
CREATE ROLE gpro_ci_rk_cabang NOLOGIN;
CREATE ROLE gpro_ci_rk_anon NOLOGIN;
CREATE ROLE gpro_ci_rk_service NOLOGIN;
CREATE SCHEMA gpro_ci_source;
CREATE SCHEMA gpro_ci_piutang;
CREATE SCHEMA gpro_ci_cabang;
CREATE TABLE gpro_ci_source.rekening_koran_working_lines_v439 (
 id uuid PRIMARY KEY,
 bank_account_code text NOT NULL,
 tanggal date NOT NULL,
 reff text,
 keterangan text,
 debet numeric NOT NULL,
 kredit numeric NOT NULL,
 saldo numeric NOT NULL,
 source_order integer,
 is_active boolean DEFAULT true,
 created_at timestamptz
);
CREATE TABLE gpro_ci_piutang.rekening_koran_working_lines_v439
 (LIKE gpro_ci_source.rekening_koran_working_lines_v439 INCLUDING ALL);
CREATE TABLE gpro_ci_cabang.journals (id integer PRIMARY KEY);
ALTER TABLE gpro_ci_piutang.rekening_koran_working_lines_v439 ENABLE ROW LEVEL SECURITY;
ALTER TABLE gpro_ci_cabang.journals ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON SCHEMA gpro_ci_source,gpro_ci_piutang,gpro_ci_cabang FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA gpro_ci_source,gpro_ci_piutang,gpro_ci_cabang FROM PUBLIC;
GRANT USAGE ON SCHEMA gpro_ci_piutang TO gpro_ci_rk_pusat,gpro_ci_rk_service;
GRANT USAGE ON SCHEMA gpro_ci_cabang TO gpro_ci_rk_cabang;
GRANT SELECT ON gpro_ci_piutang.rekening_koran_working_lines_v439 TO gpro_ci_rk_pusat;
GRANT SELECT,INSERT,UPDATE,DELETE ON gpro_ci_piutang.rekening_koran_working_lines_v439 TO gpro_ci_rk_service;
CREATE POLICY tenant_pusat_read ON gpro_ci_piutang.rekening_koran_working_lines_v439
 FOR SELECT TO gpro_ci_rk_pusat USING (true);
COMMIT;

-- Prior import version becomes inactive; new version is active.
INSERT INTO gpro_ci_source.rekening_koran_working_lines_v439
(id,bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo,source_order,is_active,created_at)
SELECT md5('legacy-'+n::text)::uuid,'BANK-TEST',
 '2026-10-01'::date+n-1,
 'REF-'||n::text,'SYNTHETIC TRANSACTION '||n::text,
 1000+n,1005+n,100000+n,n,false,'2026-11-18T04:00:00+00'::timestamptz
FROM generate_series(1,47) n;
INSERT INTO gpro_ci_source.rekening_koran_working_lines_v439
(id,bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo,source_order,is_active,created_at)
SELECT md5('replacement-'+n::text)::uuid,'BANK-TEST',
 '2026-10-01'::date+n-1,
 'REF-'||n::text,'SYNTHETIC TRANSACTION '||n::text,
 1000+n,1005+n,100000+n,n,true,'2026-11-19T04:00:00+00'::timestamptz
FROM generate_series(1,47) n;

DO $source$
DECLARE
 all_count integer;
 active_count integer;
 archived_count integer;
 paired integer;
 conflicting integer;
BEGIN
 SELECT count(*),count(*) FILTER(WHERE coalesce(is_active,true)),
        count(*) FILTER(WHERE is_active=false)
 INTO all_count,active_count,archived_count
 FROM gpro_ci_source.rekening_koran_working_lines_v439;
 SELECT count(*) INTO paired FROM (
    SELECT bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo,
     count(*) FILTER(WHERE coalesce(is_active,true)) AS act,
     count(*) FILTER(WHERE is_active=false) AS archived
    FROM gpro_ci_source.rekening_koran_working_lines_v439
    GROUP BY bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo
    HAVING count(*) FILTER(WHERE coalesce(is_active,true))=1 AND
           count(*) FILTER(WHERE is_active=false)=1
 ) x;
 SELECT count(*) INTO conflicting FROM (
    SELECT 1 FROM gpro_ci_source.rekening_koran_working_lines_v439
    GROUP BY bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo
    HAVING count(*) FILTER(WHERE coalesce(is_active,true))>1
 ) x;
 IF all_count<>94 OR active_count<>47 OR archived_count<>47 OR paired<>47 OR conflicting<>0
 THEN RAISE EXCEPTION 'EPHEMERAL NO-GO: expected versioned bank lines not present'; END IF;
END
$source$;

-- Full-history migration preserves 94 original UUIDs, not just active 47.
BEGIN ISOLATION LEVEL SERIALIZABLE;
INSERT INTO gpro_ci_piutang.rekening_koran_working_lines_v439
SELECT * FROM gpro_ci_source.rekening_koran_working_lines_v439;
DO $after_transfer$
DECLARE n_source int;n_target int;active_source numeric;active_target numeric;
BEGIN
 SELECT count(*) INTO n_source FROM gpro_ci_source.rekening_koran_working_lines_v439;
 SELECT count(*) INTO n_target FROM gpro_ci_piutang.rekening_koran_working_lines_v439;
 SELECT coalesce(sum(debet),0) INTO active_source FROM gpro_ci_source.rekening_koran_working_lines_v439 WHERE coalesce(is_active,true);
 SELECT coalesce(sum(debet),0) INTO active_target FROM gpro_ci_piutang.rekening_koran_working_lines_v439 WHERE coalesce(is_active,true);
 IF n_source<>94 OR n_target<>94 OR active_source<>active_target
    OR (SELECT count(*) FROM gpro_ci_piutang.rekening_koran_working_lines_v439 WHERE coalesce(is_active,true))<>47
 THEN RAISE EXCEPTION 'EPHEMERAL NO-GO: archive/full-history mismatch';END IF;
 IF EXISTS (
   SELECT id FROM (
      (SELECT id,is_active FROM gpro_ci_source.rekening_koran_working_lines_v439
       EXCEPT
       SELECT id,is_active FROM gpro_ci_piutang.rekening_koran_working_lines_v439)
      UNION ALL
      (SELECT id,is_active FROM gpro_ci_piutang.rekening_koran_working_lines_v439
       EXCEPT
       SELECT id,is_active FROM gpro_ci_source.rekening_koran_working_lines_v439)
   ) differences
 ) THEN RAISE EXCEPTION 'EPHEMERAL NO-GO: UUID or active flag altered';END IF;
END
$after_transfer$;
COMMIT;

DO $acl$
BEGIN
 IF has_table_privilege('gpro_ci_rk_cabang','gpro_ci_piutang.rekening_koran_working_lines_v439','SELECT') OR
    has_table_privilege('gpro_ci_rk_anon','gpro_ci_piutang.rekening_koran_working_lines_v439','SELECT') OR
    has_table_privilege('gpro_ci_rk_pusat','gpro_ci_piutang.rekening_koran_working_lines_v439','INSERT') OR
    NOT has_table_privilege('gpro_ci_rk_pusat','gpro_ci_piutang.rekening_koran_working_lines_v439','SELECT') OR
    NOT has_table_privilege('gpro_ci_rk_service','gpro_ci_piutang.rekening_koran_working_lines_v439','SELECT') OR
    NOT has_table_privilege('gpro_ci_rk_service','gpro_ci_piutang.rekening_koran_working_lines_v439','INSERT') OR
    NOT has_table_privilege('gpro_ci_rk_service','gpro_ci_piutang.rekening_koran_working_lines_v439','UPDATE') OR
    NOT has_table_privilege('gpro_ci_rk_service','gpro_ci_piutang.rekening_koran_working_lines_v439','DELETE')
 THEN RAISE EXCEPTION 'EPHEMERAL NO-GO: cross-tenant permissions'; END IF;
END
$acl$;

-- Deliberately add an illicit second active copy within a doomed transaction.
BEGIN;
INSERT INTO gpro_ci_source.rekening_koran_working_lines_v439
SELECT md5('bad-active-copy')::uuid,bank_account_code,tanggal,reff,keterangan,
       debet,kredit,saldo,source_order,true,now()
FROM gpro_ci_source.rekening_koran_working_lines_v439 WHERE source_order=1 AND is_active=true;
DO $duplicate$
DECLARE n int;
BEGIN
 SELECT count(*) INTO n FROM (
  SELECT 1 FROM gpro_ci_source.rekening_koran_working_lines_v439
  GROUP BY bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo
  HAVING count(*) FILTER(WHERE coalesce(is_active,true))>1
 ) q;
 IF n<>1 THEN RAISE EXCEPTION 'EPHEMERAL NO-GO: double-active detection failed'; END IF;
END
$duplicate$;
ROLLBACK;

DO $final$
BEGIN
 IF (SELECT count(*) FROM gpro_ci_source.rekening_koran_working_lines_v439)<>94 OR
    (SELECT count(*) FROM gpro_ci_piutang.rekening_koran_working_lines_v439)<>94
 THEN RAISE EXCEPTION 'EPHEMERAL NO-GO: rollback altered source or target'; END IF;
END
$final$;
SELECT 'GPP_RK_EPHEMERAL_PG17_ARCHIVE_PASS' AS result;
