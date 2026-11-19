-- CSB Klarin SOURCE immutable snapshot dimensions: READ ONLY.
-- Pinned Supabase project: krwoiucqfcijmihnrlem.
-- This statement does NOT lock/freeze writes across projects. An operator MUST
-- freeze source writes and obtain a matching target checkpoint separately.
-- Output is aggregate-only, contains no raw customer/claim/user/file content.
SELECT
 s.workspace_key,
 s.version AS app_state_version,
 encode(sha256(convert_to(s.state::text,'UTF8')),'hex') AS app_state_sha256,
 (SELECT count(*)::int FROM jsonb_object_keys(s.state) AS key) AS app_state_top_level_keys,
 jsonb_array_length(s.state->'monitoringKlaim') AS claim_records,
 jsonb_array_length(s.state->'uploadBatches') AS upload_batches,
 jsonb_array_length(s.state->'auditLogs') AS app_audit_events,
 (SELECT version FROM public.klarin_realtime_signal
   WHERE workspace_key=s.workspace_key) AS realtime_signal_version,
 (SELECT count(*)::bigint FROM public.klarin_stock_claim_attachments) AS attachment_rows,
 (SELECT coalesce(sum(size_bytes),0)::bigint
   FROM public.klarin_stock_claim_attachments) AS attachment_metadata_bytes,
 (SELECT count(*)::bigint FROM storage.objects WHERE bucket_id='klarin-private-attachments') AS private_object_rows,
 (SELECT coalesce(sum((metadata->>'size')::bigint),0)::bigint
   FROM storage.objects WHERE bucket_id='klarin-private-attachments') AS private_object_metadata_bytes
FROM public.klarin_stock_claim_app_state s
WHERE s.workspace_key='default';
