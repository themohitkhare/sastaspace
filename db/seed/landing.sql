INSERT INTO public.projects (slug, name, url, description, live_at)
VALUES (
  'landing',
  'SastaSpace Project Bank',
  'https://sastaspace.com',
  'Portfolio landing page for all hosted projects.',
  now()
)
ON CONFLICT (slug) DO NOTHING;
