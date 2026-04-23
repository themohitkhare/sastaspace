import Link from "next/link";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border">
        <div className="mx-auto flex h-16 max-w-5xl items-center px-6 sm:px-8">
          <Link
            href="/"
            className="flex items-center gap-3 text-foreground"
            aria-label="sastaspace home"
          >
            <BrandMark />
            <span className="text-lg font-medium tracking-tight">
              sastaspace<span className="text-[var(--brand-sasta)]">.</span>
            </span>
          </Link>
        </div>
      </header>
      <main className="flex flex-1 items-center justify-center px-4 py-12">
        <div className="w-full max-w-sm">{children}</div>
      </main>
    </div>
  );
}

function BrandMark() {
  return (
    <svg
      width="32"
      height="32"
      viewBox="0 0 80 80"
      aria-hidden="true"
      className="shrink-0"
    >
      <rect x="4" y="4" width="72" height="72" rx="12" fill="var(--brand-ink)" />
      <path
        d="M22 16 L58 16 L62 20 L62 64 L18 64 L18 20 Z"
        fill="none"
        stroke="var(--brand-sasta)"
        strokeWidth="3"
        strokeLinejoin="round"
      />
      <text
        x="40"
        y="49"
        textAnchor="middle"
        fontFamily="var(--font-inter), sans-serif"
        fontSize="24"
        fontWeight="500"
        fill="var(--brand-paper)"
        letterSpacing="-0.02em"
      >
        S
      </text>
    </svg>
  );
}
