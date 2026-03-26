import type { NextConfig } from "next";

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        // Proxy preview pages: /foo-com/preview → backend/foo-com/preview
        source: "/:subdomain/preview",
        destination: `${backendUrl}/:subdomain/preview`,
      },
      {
        // Proxy HTML downloads: /foo-com/index.html → backend/foo-com/index.html
        source: "/:subdomain/index.html",
        destination: `${backendUrl}/:subdomain/index.html`,
      },
    ];
  },
};

export default nextConfig;
