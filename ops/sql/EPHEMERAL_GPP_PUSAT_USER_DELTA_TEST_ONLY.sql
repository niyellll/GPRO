-- SYNTHETIC PostgreSQL 17 ONLY. Never run on real Supabase projects.
-- Simulate six legacy GPP Pusat accounts and five on Finance BASE.
-- A source-only user is inserted with same UUID/password/role but NO session.
-- Authentication session version increments. Existing five users are immutable.
\set ON_ERROR_STOP on

BEGIN;
CREATE ROLE gpro_ci_pusat_users_reader NOLOGIN;
CREATE ROLE gpro_ci_cabang_users_reader NOLOGIN;
CREATE ROLE gpro_ci_users_anon NOLOGIN;
CREATE ROLE gpro_ci_users_writer NOLOGIN BYPASSRLS;
CREATE SCHEMA gpro_ci_users_legacy;
CREATE SCHEMA gpro_ci_users_pusat;
REVOKE ALL ON SCHEMA gpro_ci_users_legacy,gpro_ci_users_pusat FROM PUBLIC;
GRANT USAGE ON SCHEMA gpro_ci_users_pusat TO gpro_ci_pusat_users_reader,gpro_ci_users_writer;
CREATE TABLE gpro_ci_users_legacy.users(
  id uuid PRIMARY KEY, username text NOT NULL UNIQUE, password text NOT NULL,
  role text NOT NULL, created_at timestamptz NOT NULL,
  auth_session_version bigint NOT NULL,
  active_session_id text,active_session_expires_at timestamptz,
  updated_at timestamptz
);
CREATE TABLE gpro_ci_users_pusat.users
  (LIKE gpro_ci_users_legacy.users INCLUDING ALL);
ALTER TABLE gpro_ci_users_pusat.users ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON ALL TABLES IN SCHEMA gpro_ci_users_legacy,gpro_ci_users_pusat FROM PUBLIC;
GRANT SELECT ON gpro_ci_users_pusat.users TO gpro_ci_pusat_users_reader;
GRANT SELECT,INSERT,UPDATE,DELETE ON gpro_ci_users_pusat.users TO gpro_ci_users_writer;
CREATE POLICY users_pusat_read ON gpro_ci_users_pusat.users
  FOR SELECT TO gpro_ci_pusat_users_reader USING (true);
COMMIT;

INSERT INTO gpro_ci_users_legacy.users
SELECT md5('ci-gpp-user-'||n::text)::uuid, 'synthetic-user-'||n::text,
  'synthetic-hashed-password-'||n::text, 'operator',
  '2026-11-18T08:00:00Z'::timestamptz + n * INTERVAL '1 minute',
  2,NULL,NULL,'2026-11-19T08:00:00Z'::timestamptz
FROM generate_series(1,6) n;

INSERT INTO gpro_ci_users_pusat.users
SELECT id,username,password,role,created_at,
  8,'different-target-session','2026-12-01T00:00:00Z'::timestamptz,
  '2026-11-19T09:00:00Z'::timestamptz
FROM gpro_ci_users_legacy.users
WHERE username<>'synthetic-user-6';

DO $preflight$
DECLARE stable_mismatch int;missing_users int;
BEGIN
  SELECT count(*) INTO stable_mismatch
  FROM gpro_ci_users_pusat.users t JOIN gpro_ci_users_legacy.users s USING(id)
  WHERE t.username IS DISTINCT FROM s.username OR
        t.password IS DISTINCT FROM s.password OR
        t.role IS DISTINCT FROM s.role OR
        t.created_at IS DISTINCT FROM s.created_at;
  SELECT count(*) INTO missing_users FROM gpro_ci_users_legacy.users s
    WHERE NOT EXISTS (SELECT 1 FROM gpro_ci_users_pusat.users t WHERE t.id=s.id);
  IF stable_mismatch<>0 OR missing_users<>1 OR
       (SELECT count(*) FROM gpro_ci_users_pusat.users)<>5
       OR (SELECT count(*) FROM gpro_ci_users_legacy.users)<>6
  THEN RAISE EXCEPTION 'NO-GO: synthetic missing account preflight invalid';END IF;
  IF has_table_privilege('gpro_ci_cabang_users_reader',
      'gpro_ci_users_pusat.users','SELECT') OR
     has_table_privilege('gpro_ci_users_anon','gpro_ci_users_pusat.users','SELECT') OR
     has_table_privilege('gpro_ci_pusat_users_reader',
      'gpro_ci_users_pusat.users','INSERT') OR
     NOT has_table_privilege('gpro_ci_pusat_users_reader',
      'gpro_ci_users_pusat.users','SELECT')
  THEN RAISE EXCEPTION 'NO-GO: synthetic tenant ACL compromised'; END IF;
END
$preflight$;

BEGIN ISOLATION LEVEL SERIALIZABLE;
LOCK TABLE gpro_ci_users_pusat.users IN SHARE ROW EXCLUSIVE MODE;
INSERT INTO gpro_ci_users_pusat.users
(id,username,password,role,created_at,auth_session_version,
 active_session_id,active_session_expires_at,updated_at)
SELECT s.id,s.username,s.password,s.role,s.created_at,
       s.auth_session_version+1,NULL,NULL,s.updated_at
FROM gpro_ci_users_legacy.users s
WHERE NOT EXISTS(SELECT 1 FROM gpro_ci_users_pusat.users t WHERE t.id=s.id)
AND s.active_session_id IS NULL AND s.active_session_expires_at IS NULL;

DO $verify$
DECLARE stable_diff int;existing_user_drift int;
BEGIN
  IF (SELECT count(*) FROM gpro_ci_users_pusat.users)<>6 THEN
      RAISE EXCEPTION 'NO-GO: target did not receive exactly one account';END IF;
  SELECT count(*) INTO stable_diff FROM gpro_ci_users_legacy.users s
  JOIN gpro_ci_users_pusat.users t USING (id)
  WHERE ROW(s.id,s.username,s.password,s.role,s.created_at) IS DISTINCT FROM
        ROW(t.id,t.username,t.password,t.role,t.created_at);
  IF stable_diff<>0 THEN RAISE EXCEPTION 'NO-GO: credential or role changed'; END IF;
  IF EXISTS(
    SELECT 1 FROM gpro_ci_users_pusat.users
     WHERE username='synthetic-user-6' AND
       (auth_session_version<>3 OR active_session_id IS NOT NULL
        OR active_session_expires_at IS NOT NULL)
  ) OR NOT EXISTS(SELECT 1 FROM gpro_ci_users_pusat.users
                  WHERE username='synthetic-user-6'
                  AND auth_session_version=3
                  AND active_session_id IS NULL
                  AND active_session_expires_at IS NULL)
  THEN RAISE EXCEPTION 'NO-GO: new user retained stale source session'; END IF;
  SELECT count(*) INTO existing_user_drift
  FROM gpro_ci_users_pusat.users
  WHERE username<>'synthetic-user-6'
  AND (auth_session_version<>8 OR active_session_id<>'different-target-session');
  IF existing_user_drift<>0 THEN RAISE EXCEPTION 'NO-GO: existing user session modified';END IF;
END
$verify$;
COMMIT;

-- Database constraint must reject another ID with a colliding username.
DO $unique$
BEGIN
  BEGIN
    INSERT INTO gpro_ci_users_pusat.users
    VALUES(md5('evil-other-id')::uuid,'synthetic-user-6','fake','operator',now(),1,NULL,NULL,now());
    RAISE EXCEPTION 'NO-GO: duplicate username unexpectedly inserted';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
END
$unique$;

-- Simulate overwriting an existing user inside a transaction, then rollback.
BEGIN;
UPDATE gpro_ci_users_pusat.users SET password='altered-synthetic-password'
 WHERE username='synthetic-user-1';
DO $conflict$
BEGIN
  IF NOT EXISTS (
   SELECT 1 FROM gpro_ci_users_pusat.users t
   JOIN gpro_ci_users_legacy.users s USING(id)
   WHERE t.username=s.username AND t.password IS DISTINCT FROM s.password
  ) THEN RAISE EXCEPTION 'NO-GO: stable user conflict not detected'; END IF;
END
$conflict$;
ROLLBACK;
DO $rollback$
BEGIN
  IF EXISTS (
    SELECT 1 FROM gpro_ci_users_pusat.users t JOIN gpro_ci_users_legacy.users s USING(id)
    WHERE t.password IS DISTINCT FROM s.password OR t.role IS DISTINCT FROM s.role
  ) THEN RAISE EXCEPTION 'NO-GO: rollback did not preserve credentials';END IF;
END
$rollback$;
SELECT 'GPP_PUSAT_EPHEMERAL_ONE_USER_DELTA_PASS' AS result;
