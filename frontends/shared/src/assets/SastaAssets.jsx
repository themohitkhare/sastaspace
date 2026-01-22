import React from 'react'

/**
 * SastaLogo - Pixel-art style rocket made of geometric blocks
 * Slightly "janky" DIY aesthetic with simple rectangles/squares
 */
export const SastaLogo = ({ className = "", accentColor = "#00ff00" }) => {
  return (
    <svg
      width="48"
      height="48"
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Rocket body - main rectangle */}
      <rect x="18" y="12" width="12" height="24" fill="#000000" stroke="#000000" strokeWidth="2" />
      
      {/* Rocket nose - triangle made of blocks */}
      <rect x="20" y="8" width="4" height="4" fill="#000000" />
      <rect x="24" y="4" width="4" height="4" fill={accentColor} />
      <rect x="28" y="8" width="4" height="4" fill="#000000" />
      
      {/* Rocket fins - left */}
      <rect x="12" y="28" width="6" height="4" fill="#000000" />
      <rect x="10" y="32" width="4" height="4" fill="#000000" />
      
      {/* Rocket fins - right */}
      <rect x="30" y="28" width="6" height="4" fill="#000000" />
      <rect x="34" y="32" width="4" height="4" fill="#000000" />
      
      {/* Rocket window - slightly off-center for janky look */}
      <rect x="22" y="18" width="4" height="4" fill={accentColor} />
      
      {/* Exhaust flames - geometric blocks */}
      <rect x="20" y="36" width="3" height="4" fill={accentColor} />
      <rect x="23" y="38" width="2" height="4" fill={accentColor} />
      <rect x="25" y="36" width="3" height="4" fill={accentColor} />
      <rect x="28" y="38" width="2" height="4" fill={accentColor} />
    </svg>
  )
}

/**
 * UserAvatar - Simple robot head SVG placeholder
 * Minimal geometric shapes, monochrome design
 */
export const UserAvatar = ({ className = "", size = 32 }) => {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Robot head - main square */}
      <rect x="6" y="6" width="20" height="20" fill="#000000" stroke="#000000" strokeWidth="2" />
      
      {/* Left eye */}
      <rect x="10" y="12" width="4" height="4" fill="#FFFFFF" />
      
      {/* Right eye */}
      <rect x="18" y="12" width="4" height="4" fill="#FFFFFF" />
      
      {/* Mouth - simple line */}
      <rect x="12" y="20" width="8" height="2" fill="#FFFFFF" />
      
      {/* Antenna */}
      <rect x="15" y="2" width="2" height="4" fill="#000000" />
      <rect x="14" y="0" width="4" height="2" fill="#000000" />
    </svg>
  )
}
