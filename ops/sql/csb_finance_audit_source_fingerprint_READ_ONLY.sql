-- READ ONLY: SOURCE CSB Finance audit log SHA-256 manifest.
-- Pinned Supabase project: lmbvbgkqvidtkzxtvtpe
-- Empty-safe, aggregated only; never publish raw JSON, login/user IDs or row UUID.
-- This checksum is valid ONLY for the snapshot time when the query is executed.
WITH normalized AS (
  SELECT id, encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') AS row_sha
  FROM public.audit_logs t
)
SELECT count(*)::bigint AS total_rows,
       count(DISTINCT id)::bigint AS distinct_uuids,
       encode(sha256(convert_to(
         coalesce(string_agg(row_sha,E'\\n' ORDER BY id),''),
         'UTF8')),'hex') AS sha256_all_rows
FROM normalized;
