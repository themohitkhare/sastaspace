/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "export",
  images: { unoptimized: true },
  env: {
    NEXT_PUBLIC_GOOGLE_CLIENT_ID: '867977197738-pdb93cs9rm2enujjfe13jsnd5jv67cqr.apps.googleusercontent.com',
  },
};

export default nextConfig;
