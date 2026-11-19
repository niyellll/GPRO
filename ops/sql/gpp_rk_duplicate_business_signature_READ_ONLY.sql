-- GPP Finance Pusat Rekening Koran: active-vs-archived inventory (READ ONLY).
-- Target: LEGACY source project vmpurwykfzcmculnnjfw, public schema.
-- IMPORTANT: GPP bank upload archives previous revisions (is_active=false)
-- and imports new active UUIDs (is_active=true). Identical archived rows are
-- NOT equivalent to multiple active transactions. NEVER DELETE historical rows.
-- Application treats NULL is_active as active via COALESCE(is_active,true).
-- Only aggregate counts/totals are reported; no raw transactions or UUIDs.
WITH grouped AS (
  SELECT bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo,
    count(*)::bigint AS total_copies,
    count(*) FILTER(WHERE coalesce(is_active,true))::bigint AS active_copies,
    count(*) FILTER(WHERE is_active IS FALSE)::bigint AS historical_copies,
    count(*) FILTER(WHERE is_active IS NULL)::bigint AS null_status_copies
  FROM public.rekening_koran_working_lines_v439
  GROUP BY bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo
), totals AS (
  SELECT count(*)::bigint AS all_rows,
    count(DISTINCT id)::bigint AS distinct_uuid,
    count(*) FILTER(WHERE coalesce(is_active,true))::bigint AS effective_active_rows,
    count(*) FILTER(WHERE is_active IS FALSE)::bigint AS archived_rows,
    count(*) FILTER(WHERE is_active IS NULL)::bigint AS null_status_rows,
    coalesce(sum(debet) FILTER(WHERE coalesce(is_active,true)),0) AS active_debit,
    coalesce(sum(kredit) FILTER(WHERE coalesce(is_active,true)),0) AS active_credit
  FROM public.rekening_koran_working_lines_v439
)
SELECT t.*,
  (SELECT count(*)::bigint FROM grouped) AS distinct_business_signatures,
  (SELECT count(*)::bigint FROM grouped WHERE total_copies>1)
    AS signatures_with_history_or_repeats,
  (SELECT count(*)::bigint FROM grouped
    WHERE active_copies=1 AND historical_copies=1 AND null_status_copies=0)
    AS signatures_with_one_active_one_archived,
  (SELECT count(*)::bigint FROM grouped WHERE active_copies>1)
    AS ambiguous_multiple_active_signatures,
  (SELECT coalesce(sum(active_copies),0)::bigint FROM grouped WHERE active_copies>1)
    AS rows_in_ambiguous_active_signatures,
  (SELECT count(*)::bigint FROM grouped WHERE active_copies=0)
    AS signatures_without_active_record,
  (SELECT max(total_copies)::bigint FROM grouped) AS largest_signature_history
FROM totals AS t;
