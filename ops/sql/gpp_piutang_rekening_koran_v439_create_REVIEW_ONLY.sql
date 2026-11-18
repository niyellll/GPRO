-- GPRO TWO-BASE / REVIEW ONLY
-- Prepared 2026-11-18 from LIVE source public.rekening_koran_working_lines_v439
-- SOURCE project: vmpurwykfzcmculnnjfw  (GPP Pusat)
-- TARGET project: fdhqidjltlihzdcbqfrd (bbm-finance)
-- TARGET schema: gpp_piutang
--
-- DO NOT EXECUTE until PostgreSQL+Storage full backup has been RESTORED and
-- verified in an isolated environment; data mapping and Preview routing have
-- been reviewed; source writes are frozen; operator approves the change.
-- DO NOT run against public.* (it belongs to BBM Finance in the target).
-- This creates schema structure ONLY; it does NOT import customer/financial rows.
-- This file is intentionally NOT applied by GitHub / Supabase in this PR.
--
-- FAIL-CLOSED: abort if table already exists, role missing or schema missing.
-- A repeat run is not a no-op; existing target data must be investigated.

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DO $preflight$
BEGIN
  IF to_regnamespace('gpp_piutang') IS NULL THEN
    RAISE EXCEPTION 'NO-GO: target tenant schema gpp_piutang missing';
  END IF;
  IF to_regrole('gpro_gpp_piutang_ro_v1') IS NULL THEN
    RAISE EXCEPTION 'NO-GO: GPP Pusat read-only role missing';
  END IF;
  IF to_regclass('gpp_piutang.rekening_koran_working_lines_v439') IS NOT NULL THEN
    RAISE EXCEPTION 'NO-GO: target RK table already exists; inspect before proceeding';
  END IF;
END
$preflight$;

CREATE TABLE gpp_piutang.rekening_koran_working_lines_v439 (
  id uuid PRIMARY KEY,
  bank_account_code text NOT NULL,
  bank_label text,
  tanggal date NOT NULL,
  tickmark text,
  reff text,
  keterangan text,
  debet numeric DEFAULT 0,
  kredit numeric DEFAULT 0,
  saldo numeric DEFAULT 0,
  saldo_present boolean DEFAULT false,
  source_order integer,
  checked boolean DEFAULT false,
  no_akun text DEFAULT ''::text,
  lawan_transaksi text DEFAULT ''::text,
  referensi text DEFAULT ''::text,
  posisi text DEFAULT ''::text,
  is_active boolean DEFAULT true,
  created_by text,
  updated_by text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE INDEX rekening_koran_working_bank_order_v559
  ON gpp_piutang.rekening_koran_working_lines_v439 (bank_account_code, tanggal, source_order);

ALTER TABLE gpp_piutang.rekening_koran_working_lines_v439 ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE gpp_piutang.rekening_koran_working_lines_v439
  FROM PUBLIC, anon, authenticated;

-- Read-only role: database login inherits this role; no direct write grants.
GRANT SELECT ON TABLE gpp_piutang.rekening_koran_working_lines_v439
  TO gpro_gpp_piutang_ro_v1;

-- Only the trusted, authenticated server-side layer may write using service_role.
-- A service key must NEVER be exposed to browser clients.
GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE gpp_piutang.rekening_koran_working_lines_v439
  TO service_role;

CREATE POLICY gpro_tenant_reader_select_v1
  ON gpp_piutang.rekening_koran_working_lines_v439
  FOR SELECT TO gpro_gpp_piutang_ro_v1
  USING (true);

DO $verify$
BEGIN
  IF NOT (SELECT relrowsecurity FROM pg_class
          WHERE oid = 'gpp_piutang.rekening_koran_working_lines_v439'::regclass) THEN
    RAISE EXCEPTION 'NO-GO: RK table RLS is disabled';
  END IF;
  IF has_table_privilege('gpro_gpp_cabang',
       'gpp_piutang.rekening_koran_working_lines_v439', 'SELECT')
     OR has_table_privilege('gpro_csb_finance',
       'gpp_piutang.rekening_koran_working_lines_v439', 'SELECT')
     OR has_table_privilege('authenticated',
       'gpp_piutang.rekening_koran_working_lines_v439', 'SELECT')
     OR has_table_privilege('anon',
       'gpp_piutang.rekening_koran_working_lines_v439', 'SELECT') THEN
    RAISE EXCEPTION 'NO-GO: RK tenant table has unexpected cross-role SELECT privileges';
  END IF;
  IF NOT has_table_privilege('gpro_gpp_pusat',
       'gpp_piutang.rekening_koran_working_lines_v439', 'SELECT') THEN
    RAISE EXCEPTION 'NO-GO: GPP Pusat role cannot SELECT RK';
  END IF;
END
$verify$;

COMMIT;
