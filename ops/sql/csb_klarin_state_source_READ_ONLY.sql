-- GPRO two-BASE SOURCE Klarin app-state inventory: READ ONLY
-- Project krwoiucqfcijmihnrlem;
-- Never export raw state (may contain business/PII data) to public logs.
-- Re-run source and target after an approved write freeze.
SELECT s.workspace_key,
       s.version,
       s.updated_at::date AS updated_day,
       k.key AS state_key,
       jsonb_typeof(k.value) AS state_type,
       CASE WHEN jsonb_typeof(k.value)='array'
            THEN jsonb_array_length(k.value) ELSE NULL END AS array_items,
       octet_length(k.value::text) AS content_bytes,
       encode(sha256(convert_to(k.value::text,'UTF8')),'hex') AS content_sha256
FROM public.klarin_stock_claim_app_state AS s,
     LATERAL jsonb_each(s.state) AS k
WHERE s.workspace_key='default'
ORDER BY k.key;
