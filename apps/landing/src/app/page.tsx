import Link from "next/link";
import { TopNav } from "@/components/TopNav";
import { Footer } from "@/components/Footer";
import styles from "./landing.module.css";

export default function HomePage() {
  return (
    <div className={styles.wrap}>
      <TopNav />

      <header className={styles.hero}>
        <div className={styles.heroSub}>~/mohit · sastaspace.com</div>
        <h1>
          A <span className={styles.heroAccent}>sasta</span> lab for the things I want to build.
        </h1>
        <p className={styles.heroLede}>
          This is my workshop on the open internet. I make the small things I want to exist —
          tools, toys, half-built experiments — and put them somewhere anyone can use them. Cheap
          to build. Cheap to run. Open to share.
        </p>
        <div className={styles.ctaRow}>
          <Link href="/projects" className={`${styles.btn} ${styles.btnPrimary}`}>
            see the lab →
          </Link>
          <Link href="/about" className={`${styles.btn} ${styles.btnGhost}`}>
            about the idea
          </Link>
        </div>
      </header>

      <Footer />
    </div>
  );
}
