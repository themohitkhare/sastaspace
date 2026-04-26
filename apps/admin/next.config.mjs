/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "export",
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_GOOGLE_CLIENT_ID: '867977197738-pdb93cs9rm2enujjfe13jsnd5jv67cqr.apps.googleusercontent.com',
    NEXT_PUBLIC_ADMIN_API_URL: process.env.NEXT_PUBLIC_ADMIN_API_URL ?? 'https://api.sastaspace.com',
    NEXT_PUBLIC_STDB_URI: process.env.NEXT_PUBLIC_STDB_URI ?? 'wss://stdb.sastaspace.com',
    NEXT_PUBLIC_USE_STDB_ADMIN: process.env.NEXT_PUBLIC_USE_STDB_ADMIN ?? 'false',
    NEXT_PUBLIC_OWNER_EMAIL: process.env.NEXT_PUBLIC_OWNER_EMAIL ?? 'mohitkhare582@gmail.com',
  },
};

export default nextConfig;
