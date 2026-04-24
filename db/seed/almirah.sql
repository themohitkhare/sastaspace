INSERT INTO public.projects (slug, name, url, description, live_at)
VALUES (
  'almirah',
  'Almirah',
  'https://almirah.sastaspace.com',
  'Your closet as a rack. Bulk-upload photos, AI sorts every garment into its own rail, and the app dresses you — daily picks, occasion picks, shop-the-gap.',
  now()
)
ON CONFLICT (slug) DO UPDATE
  SET name        = EXCLUDED.name,
      url         = EXCLUDED.url,
      description = EXCLUDED.description,
      live_at     = COALESCE(public.projects.live_at, EXCLUDED.live_at);
