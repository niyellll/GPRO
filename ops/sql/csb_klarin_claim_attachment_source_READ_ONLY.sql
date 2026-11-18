-- CSB Klarin source project krwoiucqfcijmihnrlem (READ ONLY).
-- No raw customer data, object keys, usernames, secret keys or filenames leave SQL.
WITH claims AS (
  SELECT entry->>'id' AS claim_id
  FROM public.klarin_stock_claim_app_state state,
       LATERAL jsonb_array_elements(state.state->'monitoringKlaim') entry
  WHERE state.workspace_key='default'
), attachments AS (
  SELECT att.id,att.owner_type,att.owner_id,att.file_name,att.size_bytes,
         att.storage_path,att.mime_type,att.data_base64,
         obj.id AS object_id, obj.name AS object_name,
         COALESCE((obj.metadata->>'size')::bigint,-1) AS object_size
  FROM public.klarin_stock_claim_attachments att
  LEFT JOIN storage.objects obj
    ON obj.bucket_id='klarin-private-attachments'
   AND obj.name=att.storage_path
)
SELECT count(*)::int AS metadata_rows,
       count(DISTINCT id)::int AS unique_metadata_ids,
       count(DISTINCT storage_path)::int AS unique_object_paths,
       count(DISTINCT owner_id)::int AS unique_owners,
       count(*) FILTER(WHERE owner_type='klaim')::int AS claim_owned_files,
       count(*) FILTER(WHERE EXISTS(SELECT 1 FROM claims WHERE claim_id=attachments.owner_id))::int AS files_with_existing_claim_owner,
       count(*) FILTER(WHERE object_id IS NOT NULL AND object_name=storage_path AND object_size=size_bytes)::int AS matching_storage_objects_and_sizes,
       count(*) FILTER(WHERE length(data_base64)=0)::int AS empty_inline_payloads,
       coalesce(sum(size_bytes),0)::bigint AS metadata_total_bytes
FROM attachments;
