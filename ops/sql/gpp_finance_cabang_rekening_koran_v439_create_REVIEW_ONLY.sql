-- GPRO TWO-BASE / REVIEW ONLY
-- Prepared 2026-11-19 for Cabang first-use compatibility; source RK table absent
-- SOURCE project: loodbfjkskduzqfthxxi (GPP Cabang)
-- TARGET project: fdhqidjltlihzdcbqfrd (bbm-finance)
-- TARGET schema: gpp_finance_cabang
--
-- DO NOT EXECUTE until PostgreSQL+Storage full backup has been RESTORED and
-- verified in an isolated environment; data mapping and Preview routing have
-- been reviewed; source writes are frozen; operator approves the change.
-- DO NOT run against public.* (it belongs to BBM Finance in the target).
-- This creates schema structure ONLY; it does NOT import customer/financial rows.
-- Cabang legacy has no RK V439 or period V543 table; the target includes
-- 3 nullable app-compatibility columns; never copy Pusat RK rows to Cabang.
-- Also prepare the empty V543 period metadata table required by the UI routes.
-- This does not fix legacy runtime ALTER/CREATE statements: Preview E2E must
-- prove they work under the proposed least-privilege role or be refactored.
-- This file is intentionally NOT applied by GitHub / Supabase in this PR.
--
-- FAIL-CLOSED: abort if table already exists, role missing or schema missing.
-- A repeat run is not a no-op; existing target data must be investigated.

BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

DO $preflight$
BEGIN
  IF to_regnamespace('gpp_finance_cabang') IS NULL THEN
    RAISE EXCEPTION 'NO-GO: target tenant schema gpp_finance_cabang missing';
  END IF;
  IF to_regrole('gpro_gpp_finance_cabang_ro_v1') IS NULL THEN
    RAISE EXCEPTION 'NO-GO: GPP Pusat read-only role missing';
  END IF;
  IF to_regclass('gpp_finance_cabang.rekening_koran_working_lines_v439') IS NOT NULL THEN
    RAISE EXCEPTION 'NO-GO: target RK table already exists; inspect before proceeding';
  END IF;
  IF to_regclass('gpp_finance_cabang.rekening_koran_period_meta_v543') IS NOT NULL THEN
    RAISE EXCEPTION 'NO-GO: target period metadata already exists; inspect before proceeding';
  END IF;
END
$preflight$;

CREATE TABLE gpp_finance_cabang.rekening_koran_working_lines_v439 (
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
  matched_journal_no text DEFAULT ''::text,
  matched_source text DEFAULT ''::text,
  attachment_note text DEFAULT ''::text,
  is_active boolean DEFAULT true,
  created_by text,
  updated_by text,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

CREATE INDEX rekening_koran_working_bank_order_v559
  ON gpp_finance_cabang.rekening_koran_working_lines_v439 (bank_account_code, tanggal, source_order);

CREATE INDEX rekening_koran_working_bank_date_v439
  ON gpp_finance_cabang.rekening_koran_working_lines_v439 (bank_account_code, tanggal, created_at);
CREATE INDEX rekening_koran_working_search_v439
  ON gpp_finance_cabang.rekening_koran_working_lines_v439 (bank_account_code, no_akun, matched_journal_no);

CREATE TABLE gpp_finance_cabang.rekening_koran_period_meta_v543 (
  bank_account_code text NOT NULL,
  period_key text NOT NULL,
  opening_balance numeric,
  closing_balance numeric,
  source_type text,
  updated_by text,
  updated_at timestamp with time zone DEFAULT now(),
  PRIMARY KEY (bank_account_code, period_key)
);

ALTER TABLE gpp_finance_cabang.rekening_koran_working_lines_v439 ENABLE ROW LEVEL SECURITY;
ALTER TABLE gpp_finance_cabang.rekening_koran_period_meta_v543 ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE gpp_finance_cabang.rekening_koran_working_lines_v439,
  gpp_finance_cabang.rekening_koran_period_meta_v543
  FROM PUBLIC, anon, authenticated;

-- Read-only role: database login inherits this role; no direct write grants.
GRANT SELECT ON TABLE gpp_finance_cabang.rekening_koran_working_lines_v439,
  gpp_finance_cabang.rekening_koran_period_meta_v543
  TO gpro_gpp_finance_cabang_ro_v1;

-- Only the trusted, authenticated server-side layer may write using service_role.
-- A service key must NEVER be exposed to browser clients.
GRANT SELECT, INSERT, UPDATE, DELETE
  ON TABLE gpp_finance_cabang.rekening_koran_working_lines_v439,
     gpp_finance_cabang.rekening_koran_period_meta_v543
  TO service_role;

CREATE POLICY gpro_tenant_reader_select_v1
  ON gpp_finance_cabang.rekening_koran_working_lines_v439
  FOR SELECT TO gpro_gpp_finance_cabang_ro_v1
  USING (true);

CREATE POLICY gpro_tenant_reader_select_v1
  ON gpp_finance_cabang.rekening_koran_period_meta_v543
  FOR SELECT TO gpro_gpp_finance_cabang_ro_v1
  USING (true);

DO $verify$
BEGIN
  IF NOT (SELECT relrowsecurity FROM pg_class
          WHERE oid = 'gpp_finance_cabang.rekening_koran_working_lines_v439'::regclass)
     OR NOT (SELECT relrowsecurity FROM pg_class
          WHERE oid = 'gpp_finance_cabang.rekening_koran_period_meta_v543'::regclass) THEN
    RAISE EXCEPTION 'NO-GO: RK table RLS is disabled';
  END IF;
  IF has_table_privilege('gpro_gpp_pusat',
       'gpp_finance_cabang.rekening_koran_working_lines_v439', 'SELECT')
     OR has_table_privilege('gpro_csb_finance',
       'gpp_finance_cabang.rekening_koran_working_lines_v439', 'SELECT')
     OR has_table_privilege('authenticated',
       'gpp_finance_cabang.rekening_koran_working_lines_v439', 'SELECT')
     OR has_table_privilege('anon',
       'gpp_finance_cabang.rekening_koran_working_lines_v439', 'SELECT') THEN
    RAISE EXCEPTION 'NO-GO: RK tenant table has unexpected cross-role SELECT privileges';
  END IF;
  IF NOT has_table_privilege('gpro_gpp_cabang',
       'gpp_finance_cabang.rekening_koran_working_lines_v439', 'SELECT')
     OR NOT has_table_privilege('gpro_gpp_cabang',
       'gpp_finance_cabang.rekening_koran_period_meta_v543', 'SELECT') THEN
    RAISE EXCEPTION 'NO-GO: GPP Cabang role cannot SELECT RK / period metadata';
  END IF;
  IF has_table_privilege('gpro_gpp_pusat',
       'gpp_finance_cabang.rekening_koran_period_meta_v543', 'SELECT')
     OR has_table_privilege('gpro_csb_finance',
       'gpp_finance_cabang.rekening_koran_period_meta_v543', 'SELECT')
     OR has_table_privilege('anon',
       'gpp_finance_cabang.rekening_koran_period_meta_v543', 'SELECT')
     OR has_table_privilege('authenticated',
       'gpp_finance_cabang.rekening_koran_period_meta_v543', 'SELECT') THEN
    RAISE EXCEPTION 'NO-GO: RK period metadata has cross-role SELECT';
  END IF;
END
$verify$;

COMMIT;
