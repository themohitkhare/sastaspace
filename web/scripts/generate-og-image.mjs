/**
 * Generate a static OG image (1200x630) for web/public/og-image.png
 * Used as fallback for crawlers that don't follow redirects.
 */
import sharp from "sharp";
import { writeFileSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, "..");

const width = 1200;
const height = 630;

// OG image SVG with SastaSpace branding
const svg = `<svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#111111"/>
      <stop offset="50%" style="stop-color:#1a1a1a"/>
      <stop offset="100%" style="stop-color:#111111"/>
    </linearGradient>
    <!-- Grid pattern -->
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.03)" stroke-width="1"/>
    </pattern>
  </defs>

  <!-- Background -->
  <rect width="${width}" height="${height}" fill="url(#bg)"/>
  <rect width="${width}" height="${height}" fill="url(#grid)"/>

  <!-- Logo mark (left side) -->
  <g transform="translate(320, 180)">
    <g transform="scale(2.5)">
      <path d="M70 25C70 25 65 10 50 10C35 10 25 22 25 32C25 52 70 42 70 62C70 75 58 90 43 90C28 90 22 75 22 75" stroke="#6366f1" stroke-width="9" stroke-linecap="round" fill="none"/>
      <circle cx="70" cy="25" r="5" fill="#e0e0e0"/>
    </g>
  </g>

  <!-- Title text -->
  <text x="600" y="280" font-family="Inter, Helvetica, Arial, sans-serif" font-size="64" font-weight="700" fill="#fafafa" letter-spacing="-2">SastaSpace</text>

  <!-- Tagline -->
  <text x="600" y="330" font-family="Inter, Helvetica, Arial, sans-serif" font-size="24" fill="#888888">
    <tspan x="600" dy="0">See your website redesigned</tspan>
    <tspan x="600" dy="34">by AI in 60 seconds</tspan>
  </text>

  <!-- Blue accent line -->
  <rect x="600" y="400" width="60" height="3" rx="2" fill="#6366f1"/>

  <!-- Bottom right domain -->
  <text x="1168" y="606" font-family="Inter, Helvetica, Arial, sans-serif" font-size="14" fill="#555555" text-anchor="end">sastaspace.com</text>
</svg>`;

async function main() {
  const png = await sharp(Buffer.from(svg)).png().toBuffer();
  const outputPath = join(projectRoot, "public/og-image.png");
  writeFileSync(outputPath, png);
  console.log(`Generated: ${outputPath} (${png.length} bytes, ${width}x${height})`);
}

main().catch(console.error);
