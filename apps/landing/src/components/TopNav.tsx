"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { BrandMark } from "@/components/BrandMark";
import { PresencePill } from "@/components/PresencePill";
import styles from "@/app/landing.module.css";

type NavItem = {
  href: string;
  label: string;
  external?: boolean;
};

const ITEMS: NavItem[] = [
  { href: "/lab", label: "the lab" },
  { href: "/projects", label: "projects" },
  { href: "https://notes.sastaspace.com", label: "notes", external: true },
  { href: "/about", label: "about" },
];

export function TopNav() {
  const pathname = usePathname();

  return (
    <nav className={styles.nav} aria-label="Primary">
      <Link href="/" className={styles.brand} aria-label="sastaspace home">
        <BrandMark className={styles.brandMark} />
        <span>
          sastaspace
          <span className={styles.brandDot} aria-hidden="true" />
        </span>
      </Link>
      <ul className={styles.navList}>
        <li>
          <PresencePill />
        </li>
        {ITEMS.map((item) => (
          <li key={item.href}>
            {item.external ? (
              <a href={item.href} className={styles.navItem}>
                {item.label}
              </a>
            ) : (
              <Link
                href={item.href}
                className={
                  isActive(pathname, item.href)
                    ? `${styles.navItem} ${styles.navItemActive}`
                    : styles.navItem
                }
                aria-current={isActive(pathname, item.href) ? "page" : undefined}
              >
                {item.label}
              </Link>
            )}
          </li>
        ))}
      </ul>
    </nav>
  );
}

function isActive(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
