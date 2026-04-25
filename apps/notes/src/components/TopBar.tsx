import Link from "next/link";
import styles from "@/app/notes.module.css";

export function TopBar() {
  return (
    <nav className={styles.nav} aria-label="Primary">
      <div className={styles.brand}>
        ~/mohit · <a href="https://sastaspace.com">sastaspace.com</a> /{" "}
        <Link href="/">notes</Link>
      </div>
      <div className={styles.navHome}>
        <a href="https://sastaspace.com">home →</a>
      </div>
    </nav>
  );
}
