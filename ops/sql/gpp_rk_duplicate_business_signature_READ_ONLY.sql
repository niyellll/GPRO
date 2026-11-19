-- GPP Finance Pusat Rekening Koran: aggregate duplicate business signature READ ONLY.
-- Pinned LEGACY source project vmpurwykfzcmculnnjfw, public schema.
-- This IS NOT a deduplication decision: legitimate distinct transactions can
-- share bank/date/reference/description/debit/credit/balance; human approval
-- and source import provenance are required before modifying any source row.
-- Only aggregate counts are reported; no transaction values or user data.
WITH duplicate_signatures AS (
  SELECT bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo,
         count(*)::bigint AS copies
  FROM public.rekening_koran_working_lines_v439
  GROUP BY bank_account_code,tanggal,reff,keterangan,debet,kredit,saldo
  HAVING count(*)>1
)
SELECT
  (SELECT count(*)::bigint FROM public.rekening_koran_working_lines_v439) AS total_rows,
  (SELECT count(DISTINCT id)::bigint FROM public.rekening_koran_working_lines_v439) AS distinct_uuid,
  count(*)::bigint AS repeated_business_signatures,
  coalesce(sum(copies),0)::bigint AS rows_in_repeated_signatures,
  coalesce(sum(copies-1),0)::bigint AS extra_copies_if_signatures_should_be_unique,
  coalesce(max(copies),0)::bigint AS largest_group
FROM duplicate_signatures;
