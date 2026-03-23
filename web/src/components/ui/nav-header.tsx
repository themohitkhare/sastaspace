"use client";

import Link from "next/link";

export function NavHeader() {
  return (
    <nav className="w-full flex items-center justify-between px-6 sm:px-8 lg:px-12 py-6 max-w-6xl mx-auto">
      <Link
        href="/"
        className="font-heading text-xl text-foreground hover:text-accent transition-colors"
      >
        SastaSpace
      </Link>
      <div className="flex items-center gap-4">
        <Link
          href="/pricing"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Pricing
        </Link>
      </div>
    </nav>
  );
}
