INSERT INTO public.projects (slug, name, url, description, live_at)
VALUES (
  'udaan',
  'udaan',
  'https://udaan.sastaspace.com',
  'Delay, cancel, and baggage risk for Indian domestic flights. Three inputs: from, to, date.',
  now()
)
ON CONFLICT (slug) DO NOTHING;
