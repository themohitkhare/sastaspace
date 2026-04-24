export function BrandMark({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 80 80" aria-hidden="true">
      <rect x="4" y="4" width="72" height="72" rx="14" fill="#1a1917" />
      <path
        d="M22 18 L56 18 L62 24 L62 64 L22 64 L22 18 Z"
        fill="none"
        stroke="#c05621"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <circle cx="55" cy="27" r="2.5" fill="#c05621" />
      <text
        x="40"
        y="53"
        textAnchor="middle"
        fontFamily="Inter, system-ui"
        fontSize="22"
        fontWeight="500"
        fill="#f5f1e8"
        letterSpacing="-0.02em"
      >
        A
      </text>
    </svg>
  );
}
