-- Post-launch fixes discovered by `scripts/verify.sh`:
--
-- 1) public.is_admin() must run as the table owner so that evaluating it from
--    inside a row-level-security qual on public.admins does not recursively
--    re-invoke RLS on public.admins (stack depth limit exceeded, SQLSTATE
--    54001). SECURITY DEFINER + a stable search_path makes the lookup safe
--    and is the standard Supabase pattern for allowlist helpers.
--
-- 2) The `anon` PostgREST role needs base privileges on the public-writable
--    shared tables. The original 0002 migration only granted INSERT to the
--    legacy `web_anon` role; RLS alone isn't enough — Postgres evaluates the
--    base grant first, so anon was getting 401 before even reaching the RLS
--    policy check.

-- 1) ------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.is_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS (
    SELECT 1 FROM public.admins a WHERE a.email = auth.email()
  );
$$;

-- SECURITY DEFINER functions must not be world-executable implicitly; lock it
-- down and re-grant to the API roles only.
REVOKE ALL ON FUNCTION public.is_admin() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION public.is_admin() TO anon, authenticated, service_role;

-- 2) ------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO anon, authenticated;

GRANT SELECT ON public.projects         TO anon, authenticated;
GRANT INSERT ON public.visits           TO anon, authenticated;
GRANT INSERT ON public.contact_messages TO anon, authenticated;

-- BIGSERIAL-backed tables need sequence USAGE for any role that can INSERT,
-- otherwise nextval() fails with 42501 before the RLS policy is even consulted.
GRANT USAGE, SELECT ON SEQUENCE public.visits_id_seq           TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.contact_messages_id_seq TO anon, authenticated;
GRANT USAGE, SELECT ON SEQUENCE public.projects_id_seq         TO authenticated;

-- Future tables / sequences created by the postgres superuser should be
-- accessible to the API roles too.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO anon, authenticated;
