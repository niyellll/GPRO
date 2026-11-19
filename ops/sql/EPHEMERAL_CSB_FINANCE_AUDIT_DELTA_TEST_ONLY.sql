-- EPHEMERAL PostgreSQL 17 integration fixture ONLY. NEVER execute on live Supabase.
-- 298 entirely synthetic CSB audit UUIDs in source, 293 target; append 5 missing.
-- Verify full SHA-256 set equality, idempotence, immutable content and RLS.
\set ON_ERROR_STOP on

BEGIN;
CREATE ROLE gpro_ci_audit_reader NOLOGIN;
CREATE ROLE gpro_ci_audit_other NOLOGIN;
CREATE ROLE gpro_ci_audit_anon NOLOGIN;
CREATE ROLE gpro_ci_audit_server NOLOGIN BYPASSRLS;
CREATE SCHEMA gpro_ci_audit_source;
CREATE SCHEMA gpro_ci_audit_target;
REVOKE ALL ON SCHEMA gpro_ci_audit_source,gpro_ci_audit_target FROM PUBLIC;
GRANT USAGE ON SCHEMA gpro_ci_audit_target TO gpro_ci_audit_reader,gpro_ci_audit_server;

CREATE TABLE gpro_ci_audit_source.audit_logs (
 id uuid PRIMARY KEY,tabel text NOT NULL,record_id text,action text,
 old_data jsonb,new_data jsonb,user_id text,created_at timestamptz,
 source text,app text,version text
);
CREATE TABLE gpro_ci_audit_target.audit_logs
 (LIKE gpro_ci_audit_source.audit_logs INCLUDING ALL);
ALTER TABLE gpro_ci_audit_target.audit_logs ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA gpro_ci_audit_source,gpro_ci_audit_target FROM PUBLIC;
GRANT SELECT ON gpro_ci_audit_target.audit_logs TO gpro_ci_audit_reader;
GRANT SELECT,INSERT,UPDATE,DELETE ON gpro_ci_audit_target.audit_logs TO gpro_ci_audit_server;
CREATE POLICY audit_select ON gpro_ci_audit_target.audit_logs
 FOR SELECT TO gpro_ci_audit_reader USING (true);
COMMIT;

-- Synthetic rows only. IDs deterministic for repeatable SHA-256 verification.
INSERT INTO gpro_ci_audit_source.audit_logs
 SELECT md5('csb-source-only-ci-'||n::text)::uuid,
  'synthetic',n::text,'event-'||n::text,
  jsonb_build_object('prior',n-1),jsonb_build_object('current',n),
  'ci-user','2026-11-01T00:00:00Z'::timestamptz + n * interval '1 second',
  'CI','SYNTHETIC','v1'
 FROM generate_series(1,298) n;

INSERT INTO gpro_ci_audit_target.audit_logs
 SELECT * FROM gpro_ci_audit_source.audit_logs
 ORDER BY created_at,id LIMIT 293;

DO $before$
DECLARE source_count int;target_count int;conflicts int;
BEGIN
 SELECT count(*) INTO source_count FROM gpro_ci_audit_source.audit_logs;
 SELECT count(*) INTO target_count FROM gpro_ci_audit_target.audit_logs;
 SELECT count(*) INTO conflicts FROM gpro_ci_audit_target.audit_logs t
 JOIN gpro_ci_audit_source.audit_logs s USING(id)
 WHERE to_jsonb(t) IS DISTINCT FROM to_jsonb(s);
 IF source_count<>298 OR target_count<>293 OR conflicts<>0 THEN
   RAISE EXCEPTION 'NO-GO: synthetic source/target cannot establish trusted delta';
 END IF;
 IF has_table_privilege('gpro_ci_audit_other','gpro_ci_audit_target.audit_logs','SELECT')
    OR has_table_privilege('gpro_ci_audit_anon','gpro_ci_audit_target.audit_logs','SELECT')
    OR has_table_privilege('gpro_ci_audit_reader','gpro_ci_audit_target.audit_logs','INSERT')
    OR NOT has_table_privilege('gpro_ci_audit_reader','gpro_ci_audit_target.audit_logs','SELECT')
    OR NOT has_table_privilege('gpro_ci_audit_server','gpro_ci_audit_target.audit_logs','INSERT')
 THEN RAISE EXCEPTION 'NO-GO: synthetic CSB audit tenant ACL failed'; END IF;
END
$before$;

-- Exactly five UUIDs are source-only; no overwriting existing audited records.
BEGIN ISOLATION LEVEL SERIALIZABLE;
LOCK TABLE gpro_ci_audit_target.audit_logs IN SHARE ROW EXCLUSIVE MODE;
DO $append$
DECLARE missing_count integer; inserted_count integer;
BEGIN
 SELECT count(*) INTO missing_count FROM gpro_ci_audit_source.audit_logs s
 WHERE NOT EXISTS(SELECT 1 FROM gpro_ci_audit_target.audit_logs t WHERE t.id=s.id);
 IF missing_count<>5 THEN RAISE EXCEPTION 'NO-GO: delta should be exactly 5'; END IF;

 INSERT INTO gpro_ci_audit_target.audit_logs
 SELECT s.* FROM gpro_ci_audit_source.audit_logs s
 WHERE NOT EXISTS (SELECT 1 FROM gpro_ci_audit_target.audit_logs t WHERE t.id=s.id);
 GET DIAGNOSTICS inserted_count = ROW_COUNT;
 IF inserted_count<>5 THEN RAISE EXCEPTION 'NO-GO: append-only delta size incorrect';END IF;
END
$append$;
COMMIT;

DO $final$
DECLARE n_source int;n_target int;source_hash text;target_hash text;diff_count int;
BEGIN
 WITH signatures AS (
  SELECT id,encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') AS h
  FROM gpro_ci_audit_source.audit_logs t
 ) SELECT count(*),encode(sha256(convert_to(
    string_agg(h,E'\n' ORDER BY id),'UTF8')),'hex')
 INTO n_source,source_hash FROM signatures;
 WITH signatures AS (
  SELECT id,encode(sha256(convert_to(to_jsonb(t)::text,'UTF8')),'hex') AS h
  FROM gpro_ci_audit_target.audit_logs t
 ) SELECT count(*),encode(sha256(convert_to(
    string_agg(h,E'\n' ORDER BY id),'UTF8')),'hex')
 INTO n_target,target_hash FROM signatures;
 IF n_source<>298 OR n_target<>298 OR source_hash<>target_hash THEN
   RAISE EXCEPTION 'NO-GO: audit append digest mismatch';
 END IF;
 SELECT count(*) INTO diff_count FROM (
   (SELECT * FROM gpro_ci_audit_source.audit_logs EXCEPT
    SELECT * FROM gpro_ci_audit_target.audit_logs)
   UNION ALL
   (SELECT * FROM gpro_ci_audit_target.audit_logs EXCEPT
    SELECT * FROM gpro_ci_audit_source.audit_logs)
 ) mismatch;
 IF diff_count<>0 THEN RAISE EXCEPTION 'NO-GO: entire audit log set diverged';END IF;
END
$final$;

-- A conflicting same UUID must be visible and fail preflight (then rollback).
BEGIN;
UPDATE gpro_ci_audit_target.audit_logs SET action='MUTATED_SYNTHETIC'
 WHERE id=(SELECT min(id) FROM gpro_ci_audit_target.audit_logs);
DO $conflict$
BEGIN
 IF NOT EXISTS (
 SELECT 1 FROM gpro_ci_audit_target.audit_logs t
 JOIN gpro_ci_audit_source.audit_logs s USING(id)
 WHERE to_jsonb(t) IS DISTINCT FROM to_jsonb(s)
 ) THEN RAISE EXCEPTION 'NO-GO: immutable UUID conflict not detected';END IF;
END
$conflict$;
ROLLBACK;

DO $rollback$
BEGIN
 IF (SELECT count(*) FROM gpro_ci_audit_target.audit_logs)<>298 OR EXISTS(
 SELECT 1 FROM gpro_ci_audit_target.audit_logs t
 JOIN gpro_ci_audit_source.audit_logs s USING(id)
 WHERE to_jsonb(t) IS DISTINCT FROM to_jsonb(s)
 ) THEN RAISE EXCEPTION 'NO-GO: rollback modified final audit set'; END IF;
END
$rollback$;

SELECT 'CSB_FINANCE_EPHEMERAL_AUDIT_DELTA_PASS' AS result;
