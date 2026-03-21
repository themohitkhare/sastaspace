/**
 * Generate static icon assets for PWA manifest and favicon.
 * Uses sharp to render SVG to PNG at various sizes.
 */
import sharp from "sharp";
import { writeFileSync, mkdirSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = join(__dirname, "..");

// SVG icon: stylized "S" lettermark on dark background with blue accent
function createIconSvg(size) {
  const borderRadius = Math.round(size * 0.18);
  const strokeWidth = size <= 32 ? 12 : 10;
  const dotRadius = size <= 32 ? 4 : 5;

  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1a1a1a"/>
      <stop offset="100%" style="stop-color:#2a2a2a"/>
    </linearGradient>
  </defs>
  <rect width="${size}" height="${size}" rx="${borderRadius}" fill="url(#bg)"/>
  <g transform="translate(${size * 0.15}, ${size * 0.1}) scale(${size * 0.007})">
    <path d="M70 25C70 25 65 10 50 10C35 10 25 22 25 32C25 52 70 42 70 62C70 75 58 90 43 90C28 90 22 75 22 75" stroke="#6366f1" stroke-width="${strokeWidth}" stroke-linecap="round" fill="none"/>
    <circle cx="70" cy="25" r="${dotRadius}" fill="#e0e0e0"/>
  </g>
</svg>`;
}

// Generate favicon.ico (multi-size ICO file via PNG conversion)
async function generateFavicon() {
  const svg16 = createIconSvg(16);
  const svg32 = createIconSvg(32);

  // Generate 32x32 PNG and use as favicon (browsers handle PNG favicons fine)
  const png32 = await sharp(Buffer.from(svg32)).png().toBuffer();

  // For .ico, we'll use a 32x32 PNG — modern browsers support PNG in ICO
  // Create a proper ICO file with PNG payload
  const icoHeader = Buffer.alloc(6);
  icoHeader.writeUInt16LE(0, 0); // Reserved
  icoHeader.writeUInt16LE(1, 2); // ICO type
  icoHeader.writeUInt16LE(1, 4); // 1 image

  const dirEntry = Buffer.alloc(16);
  dirEntry.writeUInt8(32, 0); // Width
  dirEntry.writeUInt8(32, 1); // Height
  dirEntry.writeUInt8(0, 2); // Color palette
  dirEntry.writeUInt8(0, 3); // Reserved
  dirEntry.writeUInt16LE(1, 4); // Color planes
  dirEntry.writeUInt16LE(32, 6); // Bits per pixel
  dirEntry.writeUInt32LE(png32.length, 8); // Size of image data
  dirEntry.writeUInt32LE(22, 12); // Offset (6 header + 16 dir entry)

  const ico = Buffer.concat([icoHeader, dirEntry, png32]);
  const faviconPath = join(projectRoot, "src/app/favicon.ico");
  writeFileSync(faviconPath, ico);
  console.log(`Generated: ${faviconPath} (${ico.length} bytes)`);
}

// Generate PNG icons at specified sizes
async function generatePng(size, outputPath) {
  const svg = createIconSvg(size);
  const png = await sharp(Buffer.from(svg)).resize(size, size).png().toBuffer();

  const fullPath = join(projectRoot, outputPath);
  mkdirSync(dirname(fullPath), { recursive: true });
  writeFileSync(fullPath, png);
  console.log(`Generated: ${fullPath} (${png.length} bytes, ${size}x${size})`);
}

async function main() {
  console.log("Generating SastaSpace icon assets...\n");

  await generateFavicon();
  await generatePng(192, "public/icon-192.png");
  await generatePng(512, "public/icon-512.png");

  console.log("\nAll icons generated successfully.");
}

main().catch(console.error);
