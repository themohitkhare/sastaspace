DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'project_almirah') THEN
    CREATE ROLE project_almirah NOLOGIN;
  END IF;
END $$;

CREATE SCHEMA IF NOT EXISTS project_almirah AUTHORIZATION project_almirah;
GRANT USAGE ON SCHEMA project_almirah TO web_anon;
