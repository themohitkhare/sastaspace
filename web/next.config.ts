import type { NextConfig } from "next";

// Rewrite destination for server-side proxying of preview/download URLs.
// In k8s: INTERNAL_BACKEND_URL=http://backend:8080 (cluster-internal)
// In dev: falls back to localhost:8080
const rewriteBackend =
  process.env.INTERNAL_BACKEND_URL || "http://localhost:8080";

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/:subdomain/preview",
        destination: `${rewriteBackend}/:subdomain/preview`,
      },
      {
        source: "/:subdomain/index.html",
        destination: `${rewriteBackend}/:subdomain/index.html`,
      },
    ];
  },
};

export default nextConfig;
