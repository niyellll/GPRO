-- GPRO TWO-BASE: TARGET READ ONLY
-- Execute in the correct Supabase project on a CONSISTENT SNAPSHOT after write freeze.
-- Source project: vmpurwykfzcmculnnjfw / public
-- Target project: fdhqidjltlihzdcbqfrd / gpp_piutang
-- Compare returned row_count, unique_ids, debit_total, credit_total and content_sha256.
-- Target includes 3 extra compatibility columns; these are EXCLUDED from digest.
-- Neither query modifies data or discloses transaction rows.
WITH normalized AS (
  SELECT id,
    (to_jsonb(t)
      - 'matched_journal_no'
      - 'matched_source'
      - 'attachment_note')::text AS record_text,
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
