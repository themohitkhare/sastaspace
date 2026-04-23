-- Admin allowlist + convenience predicates used across projects.

CREATE TABLE IF NOT EXISTS public.admins (
  email TEXT PRIMARY KEY,
  note TEXT,
  added_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO public.admins (email, note)
VALUES ('mohitkhare582@gmail.com', 'owner')
ON CONFLICT (email) DO NOTHING;

CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.admins a WHERE a.email = auth.email()
  );
$$;

GRANT EXECUTE ON FUNCTION public.is_admin() TO anon, authenticated, service_role;

ALTER TABLE public.admins ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS admins_self_select ON public.admins;
CREATE POLICY admins_self_select ON public.admins
  FOR SELECT
  USING (email = auth.email() OR public.is_admin());

DROP POLICY IF EXISTS admins_service_write ON public.admins;
CREATE POLICY admins_service_write ON public.admins
  FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS projects_public_read ON public.projects;
CREATE POLICY projects_public_read ON public.projects
  FOR SELECT USING (live_at IS NOT NULL);
DROP POLICY IF EXISTS projects_admin_write ON public.projects;
CREATE POLICY projects_admin_write ON public.projects
  FOR ALL
  USING (public.is_admin() OR auth.role() = 'service_role')
  WITH CHECK (public.is_admin() OR auth.role() = 'service_role');

ALTER TABLE public.contact_messages ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS contact_messages_insert_any ON public.contact_messages;
CREATE POLICY contact_messages_insert_any ON public.contact_messages
  FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS contact_messages_admin_read ON public.contact_messages;
CREATE POLICY contact_messages_admin_read ON public.contact_messages
  FOR SELECT USING (public.is_admin() OR auth.role() = 'service_role');

ALTER TABLE public.visits ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS visits_insert_any ON public.visits;
CREATE POLICY visits_insert_any ON public.visits
  FOR INSERT WITH CHECK (true);
DROP POLICY IF EXISTS visits_admin_read ON public.visits;
CREATE POLICY visits_admin_read ON public.visits
  FOR SELECT USING (public.is_admin() OR auth.role() = 'service_role');
