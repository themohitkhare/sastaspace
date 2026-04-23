CREATE TABLE IF NOT EXISTS public.projects (
  id BIGSERIAL PRIMARY KEY,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  url TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  live_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.visits (
  id BIGSERIAL PRIMARY KEY,
  project_slug TEXT NOT NULL,
  referrer TEXT,
  ua TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.contact_messages (
  id BIGSERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  message TEXT NOT NULL,
  source_project TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_projects_live_at ON public.projects (live_at DESC);
CREATE INDEX IF NOT EXISTS idx_visits_project_slug_created_at ON public.visits (project_slug, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_contact_messages_source_project_created_at ON public.contact_messages (source_project, created_at DESC);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'web_anon') THEN
    CREATE ROLE web_anon NOLOGIN;
  END IF;
END $$;

GRANT USAGE ON SCHEMA public TO web_anon;
GRANT SELECT ON public.projects TO web_anon;
GRANT INSERT ON public.visits TO web_anon;
GRANT INSERT ON public.contact_messages TO web_anon;
