-- GPRO TWO-BASE: TARGET READ ONLY
-- Execute in the correct Supabase project on a CONSISTENT SNAPSHOT after write freeze.
-- Source project: vmpurwykfzcmculnnjfw / public
-- Target project: fdhqidjltlihzdcbqfrd / gpp_piutang
-- Compare returned row_count, unique_ids, debit_total, credit_total and content_sha256.
-- Exactly 22 original source columns are projected; target-only compatibility columns cannot enter digest.
-- Neither query modifies data or discloses transaction rows.
WITH normalized AS (
  SELECT id,
    jsonb_build_object(
      'id', t.id,
      'bank_account_code', t.bank_account_code,
      'bank_label', t.bank_label,
      'tanggal', t.tanggal,
      'tickmark', t.tickmark,
      'reff', t.reff,
      'keterangan', t.keterangan,
      'debet', t.debet,
      'kredit', t.kredit,
      'saldo', t.saldo,
      'saldo_present', t.saldo_present,
      'source_order', t.source_order,
      'checked', t.checked,
      'no_akun', t.no_akun,
      'lawan_transaksi', t.lawan_transaksi,
      'referensi', t.referensi,
      'posisi', t.posisi,
      'is_active', t.is_active,
      'created_by', t.created_by,
      'updated_by', t.updated_by,
      'created_at', t.created_at,
      'updated_at', t.updated_at
    )::text AS record_text,
    debet, kredit, tanggal
  FROM gpp_piutang.rekening_koran_working_lines_v439 AS t
), summary AS (
  SELECT
    count(*)::bigint AS row_count,
    count(DISTINCT id)::bigint AS unique_ids,
    COALESCE(sum(debet),0) AS debit_total,
    COALESCE(sum(kredit),0) AS credit_total,
    min(tanggal) AS first_date,
    max(tanggal) AS last_date,
    encode(sha256(convert_to(COALESCE(string_agg(record_text, E'\n' ORDER BY id),''),'UTF8')),'hex') AS content_sha256
  FROM normalized
)
SELECT * FROM summary;
