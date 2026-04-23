import Link from "next/link";

type NavLink = { href: string; label: string };

const DEFAULT_NAV: NavLink[] = [
  { href: "/#lab", label: "the lab" },
  { href: "/#projects", label: "projects" },
  { href: "/#notes", label: "notes" },
  { href: "/#about", label: "about" },
];

export function Topbar({ nav = DEFAULT_NAV }: { nav?: NavLink[] }) {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6 sm:px-8">
        <Link
          href="/"
          className="flex items-center gap-3 text-foreground"
          aria-label="sastaspace home"
        >
          <BrandMark />
          <span className="text-lg font-medium tracking-tight sm:text-xl">
            sastaspace<span className="text-[var(--brand-sasta)]">.</span>
          </span>
        </Link>
        <nav aria-label="primary">
          <ul className="hidden items-center gap-6 font-mono text-[13px] text-foreground sm:flex">
            {nav.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="transition-colors hover:text-[var(--brand-sasta)]"
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
          {/* On mobile we fall back to a single contact link — anchor nav is redundant with scroll */}
          <Link
            href="/contact"
            className="font-mono text-[13px] text-foreground transition-colors hover:text-[var(--brand-sasta)] sm:hidden"
          >
            contact
          </Link>
        </nav>
      </div>
    </header>
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
        fontFamily="Inter, system-ui, sans-serif"
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
