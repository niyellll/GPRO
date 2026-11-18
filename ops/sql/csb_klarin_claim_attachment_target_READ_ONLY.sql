-- CSB Klarin target BASE numlkqppirrxfwdhazja (READ ONLY).
-- Compare against source after freeze; do not treat empty target as migration success.
SELECT (SELECT count(*) FROM csb_klarin.klarin_stock_claim_attachments)::int AS tenant_metadata_rows,
       (SELECT count(*) FROM storage.objects
         WHERE bucket_id='gpro-csb-private-attachments')::int AS tenant_storage_objects,
       (SELECT public FROM storage.buckets
         WHERE id='gpro-csb-private-attachments') AS tenant_bucket_is_public,
       (SELECT version FROM csb_klarin.klarin_stock_claim_app_state
         WHERE workspace_key='default') AS tenant_state_version,
       (SELECT version FROM csb_klarin.klarin_realtime_signal
         WHERE workspace_key='default') AS tenant_realtime_version,
       (SELECT relrowsecurity FROM pg_class
         WHERE oid='csb_klarin.klarin_stock_claim_attachments'::regclass) AS metadata_rls_enabled,
       has_table_privilege('anon','csb_klarin.klarin_stock_claim_attachments','SELECT') AS anon_metadata_can_read,
       has_table_privilege('authenticated','csb_klarin.klarin_stock_claim_attachments','SELECT') AS authenticated_metadata_can_read;
