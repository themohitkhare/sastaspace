/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "export",
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_GOOGLE_CLIENT_ID: '867977197738-pdb93cs9rm2enujjfe13jsnd5jv67cqr.apps.googleusercontent.com',
    // Empty default so a misconfigured build fails loud (callers throw) rather
    // than calling https://api.sastaspace.com which is removed in Phase 3 B5.
    // Set NEXT_PUBLIC_USE_STDB_ADMIN=true (the post-cutover prod build) to skip
    // the legacy path entirely.
    NEXT_PUBLIC_ADMIN_API_URL: process.env.NEXT_PUBLIC_ADMIN_API_URL ?? '',
    NEXT_PUBLIC_STDB_URI: process.env.NEXT_PUBLIC_STDB_URI ?? 'wss://stdb.sastaspace.com',
    NEXT_PUBLIC_USE_STDB_ADMIN: process.env.NEXT_PUBLIC_USE_STDB_ADMIN ?? 'false',
    NEXT_PUBLIC_OWNER_EMAIL: process.env.NEXT_PUBLIC_OWNER_EMAIL ?? 'mohitkhare582@gmail.com',
  },
};

export default nextConfig;
