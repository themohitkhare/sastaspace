import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/pricing"],
      disallow: "/api/",
    },
    sitemap: "https://sastaspace.com/sitemap.xml",
  };
}
