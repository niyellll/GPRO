-- EPHEMERAL PostgreSQL 17 test ONLY. NEVER apply to Supabase production.
-- All role names and customer/attachment values are synthetic fixtures.
-- Run on disposable GitHub Actions PostgreSQL service with ON_ERROR_STOP=1.
\set ON_ERROR_STOP on

BEGIN;
CREATE ROLE gpro_ci_csb_reader NOLOGIN;
CREATE ROLE gpro_ci_gpp_reader NOLOGIN;
CREATE ROLE gpro_ci_anon NOLOGIN;
CREATE ROLE gpro_ci_service NOLOGIN;
CREATE SCHEMA gpro_ci_csb;
CREATE SCHEMA gpro_ci_gpp;

CREATE TABLE gpro_ci_csb.claim_state (
  workspace_key text PRIMARY KEY,
  state jsonb NOT NULL,
  version bigint NOT NULL,
  updated_by text NOT NULL DEFAULT '',
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE gpro_ci_csb.signal (
  workspace_key text PRIMARY KEY,
  version bigint NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE gpro_ci_csb.attachments (
  id text PRIMARY KEY,
  owner_type text NOT NULL,
  owner_id text NOT NULL,
  file_name text NOT NULL,
  size_bytes bigint NOT NULL CHECK (size_bytes>0),
  UNIQUE(owner_type,owner_id,file_name)
);
CREATE TABLE gpro_ci_gpp.stock (id text PRIMARY KEY);
ALTER TABLE gpro_ci_csb.claim_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE gpro_ci_csb.signal ENABLE ROW LEVEL SECURITY;
ALTER TABLE gpro_ci_csb.attachments ENABLE ROW LEVEL SECURITY;
ALTER TABLE gpro_ci_gpp.stock ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON SCHEMA gpro_ci_csb, gpro_ci_gpp FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA gpro_ci_csb, gpro_ci_gpp FROM PUBLIC;
GRANT USAGE ON SCHEMA gpro_ci_csb TO gpro_ci_csb_reader, gpro_ci_service;
GRANT USAGE ON SCHEMA gpro_ci_gpp TO gpro_ci_gpp_reader, gpro_ci_service;
GRANT SELECT ON ALL TABLES IN SCHEMA gpro_ci_csb TO gpro_ci_csb_reader;
GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA gpro_ci_csb TO gpro_ci_service;
GRANT SELECT ON ALL TABLES IN SCHEMA gpro_ci_gpp TO gpro_ci_gpp_reader;
CREATE POLICY csb_select ON gpro_ci_csb.claim_state
  FOR SELECT TO gpro_ci_csb_reader USING (true);
CREATE POLICY csb_signal_select ON gpro_ci_csb.signal
  FOR SELECT TO gpro_ci_csb_reader USING (true);
CREATE POLICY csb_attachment_select ON gpro_ci_csb.attachments
  FOR SELECT TO gpro_ci_csb_reader USING (true);

INSERT INTO gpro_ci_csb.claim_state(workspace_key,state,version) VALUES
 ('default','{"monitoringKlaim":[],"uploadBatches":[{"id":"old-batch"}],"auditLogs":[{"id":"old-log"}],"other":{"safe":true}}',38);
INSERT INTO gpro_ci_csb.signal(workspace_key,version) VALUES ('default',38);
COMMIT;

DO $isolation$
DECLARE
  denied integer;
BEGIN
  IF has_schema_privilege('gpro_ci_gpp_reader','gpro_ci_csb','USAGE') OR
     has_table_privilege('gpro_ci_gpp_reader','gpro_ci_csb.claim_state','SELECT') OR
     has_table_privilege('gpro_ci_gpp_reader','gpro_ci_csb.attachments','SELECT') OR
     has_table_privilege('gpro_ci_anon','gpro_ci_csb.claim_state','SELECT') OR
     has_table_privilege('gpro_ci_csb_reader','gpro_ci_gpp.stock','SELECT') OR
     has_table_privilege('gpro_ci_csb_reader','gpro_ci_csb.claim_state','INSERT') OR
     has_table_privilege('gpro_ci_csb_reader','gpro_ci_csb.claim_state','UPDATE') THEN
    RAISE EXCEPTION 'EPHEMERAL NO-GO: least-privilege cross-tenant isolation failed';
  END IF;
  IF NOT has_table_privilege('gpro_ci_csb_reader','gpro_ci_csb.claim_state','SELECT')
     OR NOT has_table_privilege('gpro_ci_service','gpro_ci_csb.claim_state','SELECT')
     OR NOT has_table_privilege('gpro_ci_service','gpro_ci_csb.claim_state','INSERT')
     OR NOT has_table_privilege('gpro_ci_service','gpro_ci_csb.claim_state','UPDATE')
     OR NOT has_table_privilege('gpro_ci_service','gpro_ci_csb.claim_state','DELETE') THEN
    RAISE EXCEPTION 'EPHEMERAL NO-GO: role grants not all separately validated';
  END IF;
END
$isolation$;

-- Synthetic transfer must succeed exactly once when expected old JSON+version match.
BEGIN ISOLATION LEVEL SERIALIZABLE;
LOCK TABLE gpro_ci_csb.attachments IN SHARE ROW EXCLUSIVE MODE;
DO $cas$
DECLARE
  old_json jsonb;
  updated bigint;
  signal_updated bigint;
  merged jsonb;
BEGIN
  SELECT state INTO old_json FROM gpro_ci_csb.claim_state
   WHERE workspace_key='default';
  merged = '{
     "monitoringKlaim":[{"id":"claim-1","status":"draft"}],
     "uploadBatches":[{"id":"old-batch"},{"id":"new-batch"}],
     "auditLogs":[{"id":"old-log"},{"id":"new-log"}],
     "other":{"safe":true}
  }'::jsonb;
  INSERT INTO gpro_ci_csb.attachments(id,owner_type,owner_id,file_name,size_bytes)
   VALUES('file-1','klaim','claim-1','synthetic.pdf',64);
  UPDATE gpro_ci_csb.claim_state
     SET state=merged, version=40, updated_by='GPRO_CI_SYNTHETIC',updated_at=now()
   WHERE workspace_key='default' AND version=38 AND state=old_json
   RETURNING version INTO updated;
  IF updated IS DISTINCT FROM 40 THEN
    RAISE EXCEPTION 'EPHEMERAL NO-GO: version+state CAS did not update exactly once';
  END IF;
  UPDATE gpro_ci_csb.signal SET version=40,updated_at=now()
   WHERE workspace_key='default' AND version=38
   RETURNING version INTO signal_updated;
  IF signal_updated IS DISTINCT FROM 40 THEN
    RAISE EXCEPTION 'EPHEMERAL NO-GO: realtime signal CAS failed';
  END IF;
END
$cas$;
COMMIT;

-- A stale Preview session trying to repeat version=38 MUST update zero rows.
DO $reject_stale$
DECLARE
  updated_rows integer;
BEGIN
  UPDATE gpro_ci_csb.claim_state
     SET state='{}'::jsonb,version=41
   WHERE workspace_key='default' AND version=38;
  GET DIAGNOSTICS updated_rows = ROW_COUNT;
  IF updated_rows<>0 THEN
    RAISE EXCEPTION 'EPHEMERAL NO-GO: stale application state overwrote new version';
  END IF;
  IF (SELECT version FROM gpro_ci_csb.claim_state WHERE workspace_key='default')<>40 OR
     (SELECT version FROM gpro_ci_csb.signal WHERE workspace_key='default')<>40 OR
     (SELECT count(*) FROM gpro_ci_csb.attachments)<>1 OR
     (SELECT jsonb_array_length(state->'monitoringKlaim')
        FROM gpro_ci_csb.claim_state WHERE workspace_key='default')<>1 THEN
    RAISE EXCEPTION 'EPHEMERAL NO-GO: final claim state and file metadata incomplete';
  END IF;
END
$reject_stale$;

-- Synthetic rollback must not leave a partial edit or a second attachment.
BEGIN;
INSERT INTO gpro_ci_csb.attachments(id,owner_type,owner_id,file_name,size_bytes)
 VALUES('file-2','klaim','claim-1','cancelled.pdf',64);
UPDATE gpro_ci_csb.claim_state SET version=99 WHERE workspace_key='default';
ROLLBACK;

DO $rollback$
BEGIN
  IF (SELECT version FROM gpro_ci_csb.claim_state WHERE workspace_key='default')<>40
     OR (SELECT count(*) FROM gpro_ci_csb.attachments)<>1 THEN
    RAISE EXCEPTION 'EPHEMERAL NO-GO: rollback did not preserve last committed data';
  END IF;
END
$rollback$;

SELECT 'CSB_KLARIN_EPHEMERAL_PG17_CAS_PASS' AS result;
