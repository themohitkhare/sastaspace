/**
 * Generate static PNG icon files for PWA manifest.
 * Run: node scripts/generate-static-icons.mjs
 *
 * Uses sharp if available, otherwise creates simple SVG-based placeholders.
 * The dynamic Next.js icon.tsx / apple-icon.tsx routes are the primary icons;
 * these static PNGs are fallbacks for the web manifest.
 */

import { writeFileSync } from "fs";

// SVG template for the S lettermark on gradient background
function createIconSvg(size) {
  const radius = Math.round(size * 0.15);
  const sSize = Math.round(size * 0.6);
  const sOffset = Math.round((size - sSize) / 2);
  const strokeWidth = Math.round(sSize * 0.16);

  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#7c3aed"/>
      <stop offset="50%" stop-color="#4f46e5"/>
      <stop offset="100%" stop-color="#3730a3"/>
    </linearGradient>
  </defs>
  <rect width="${size}" height="${size}" rx="${radius}" fill="url(#bg)"/>
  <g transform="translate(${sOffset}, ${sOffset})">
    <path
      d="M${sSize*0.68} ${sSize*0.28}C${sSize*0.68} ${sSize*0.14} ${sSize*0.56} ${sSize*0.06} ${sSize*0.44} ${sSize*0.06}C${sSize*0.32} ${sSize*0.06} ${sSize*0.22} ${sSize*0.14} ${sSize*0.22} ${sSize*0.26}C${sSize*0.22} ${sSize*0.38} ${sSize*0.32} ${sSize*0.42} ${sSize*0.44} ${sSize*0.46}C${sSize*0.56} ${sSize*0.50} ${sSize*0.68} ${sSize*0.54} ${sSize*0.68} ${sSize*0.66}C${sSize*0.68} ${sSize*0.78} ${sSize*0.56} ${sSize*0.86} ${sSize*0.44} ${sSize*0.86}C${sSize*0.32} ${sSize*0.86} ${sSize*0.22} ${sSize*0.78} ${sSize*0.22} ${sSize*0.64}"
      stroke="rgba(255,255,255,0.95)"
      stroke-width="${strokeWidth}"
      stroke-linecap="round"
      fill="none"
    />
  </g>
</svg>`;
}

// Write SVG files (browsers can use SVG in manifests, or convert to PNG externally)
writeFileSync("public/icon-192.svg", createIconSvg(192));
writeFileSync("public/icon-512.svg", createIconSvg(512));

console.log("Generated icon-192.svg and icon-512.svg in public/");
console.log("Note: For PNG versions, use an image converter or let Next.js dynamic routes handle it.");
