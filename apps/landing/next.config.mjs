/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Static export — landing has no server-side data; SpacetimeDB is contacted
  // entirely from the browser. Output goes to ./out, deployed to Cloudflare Pages.
  output: 'export',
  images: { unoptimized: true },
  transpilePackages: ['@sastaspace/design-tokens'],
};

export default nextConfig;
