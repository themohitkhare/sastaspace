import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-16 border-t border-border">
      <div className="mx-auto max-w-5xl px-6 py-12 sm:px-8 sm:py-14">
        <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-end">
          <div className="font-mono text-[13px] leading-relaxed text-muted-foreground">
            Built <span className="font-medium text-foreground">sasta</span>. Shared openly.
            <br />© Mohit Khare, {new Date().getFullYear()}.
          </div>
          <ul className="flex gap-5 font-mono text-[13px]">
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
                href="https://linkedin.com/in/themohitkhare"
                target="_blank"
                rel="noreferrer"
                className="text-foreground transition-colors hover:text-[var(--brand-sasta)]"
              >
                linkedin
              </Link>
            </li>
            <li>
              <Link
                href="/rss.xml"
                className="text-foreground transition-colors hover:text-[var(--brand-sasta)]"
              >
                rss
              </Link>
            </li>
            <li>
              <Link
                href="/contact"
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
