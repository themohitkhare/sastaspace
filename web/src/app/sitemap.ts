import type { MetadataRoute } from "next";

const BASE_URL = process.env.NEXT_PUBLIC_BASE_URL || "https://sastaspace.com";

export default function sitemap(): MetadataRoute.Sitemap {
  const staticRoutes: MetadataRoute.Sitemap = [
    {
      url: BASE_URL,
      lastModified: new Date(),
      changeFrequency: "weekly",
      priority: 1,
    },
  ];

  // TODO: Fetch dynamic subdomain entries from the backend registry API
  // e.g. const response = await fetch(`${BACKEND_URL}/api/sites`);
  //      const sites = await response.json();
  //      const dynamicRoutes = sites.map(s => ({
  //        url: `${BASE_URL}/${s.subdomain}`,
  //        lastModified: new Date(s.created_at),
  //        changeFrequency: "monthly" as const,
  //        priority: 0.6,
  //      }));
  // For now, only static routes are included until the backend exposes a sites listing endpoint.

  return staticRoutes;
}
