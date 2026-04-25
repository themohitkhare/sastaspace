export function BrandMark({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 80 80" role="img" aria-hidden="true">
      <rect x="4" y="4" width="72" height="72" rx="12" fill="#1a1917" />
      <path
        d="M22 16 L58 16 L62 20 L62 64 L18 64 L18 20 Z"
        fill="none"
        stroke="#c05621"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <text
        x="40"
        y="49"
        textAnchor="middle"
        fontFamily="Inter, ui-sans-serif, system-ui"
        fontSize="26"
        fontWeight="500"
        fill="#f5f1e8"
        letterSpacing="-0.02em"
      >
        S
      </text>
    </svg>
  );
}
