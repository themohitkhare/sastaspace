import Link from "next/link";

/**
 * Shared footer for every sastaspace.com subdomain.
 * Wire it into your project's layout to stay on-brand.
 *
 * See brand/BRAND_GUIDE.md §10 for the roll-out checklist.
 */
export function BrandFooter({
  projectName = "__NAME__",
}: {
  projectName?: string;
}) {
  return (
    <footer className="mt-16 border-t border-border">
      <div className="mx-auto max-w-5xl px-6 py-12 sm:px-8 sm:py-14">
        <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-end">
          <div className="font-mono text-[13px] leading-relaxed text-muted-foreground">
            Part of <Link
              href="https://sastaspace.com"
              className="text-foreground transition-colors hover:text-[var(--brand-sasta)]"
            >sastaspace</Link> · {projectName}
            <br />
            Built <span className="font-medium text-foreground">sasta</span>. Shared openly.
          </div>
          <ul className="flex gap-5 font-mono text-[13px]">
            <li>
              <Link
                href="https://sastaspace.com"
                className="text-foreground transition-colors hover:text-[var(--brand-sasta)]"
              >
                ← the lab
              </Link>
            </li>
            <li>
              <Link
                href="https://github.com/themohitkhare"
                target="_blank"
                rel="noreferrer"
                className="text-foreground transition-colors hover:text-[var(--brand-sasta)]"
              >
                github
              </Link>
            </li>
            <li>
              <Link
                href="https://sastaspace.com/contact"
                className="text-foreground transition-colors hover:text-[var(--brand-sasta)]"
              >
                contact
              </Link>
            </li>
          </ul>
        </div>
        <div className="mt-6 font-deva text-sm text-[var(--brand-dust)]">
          जो बनाना है, बनाओ.
        </div>
      </div>
    </footer>
  );
}
