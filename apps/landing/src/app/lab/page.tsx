import { TopNav } from "@/components/TopNav";
import { Footer } from "@/components/Footer";
import styles from "../landing.module.css";

export const metadata = {
  title: "the lab — sastaspace",
  description: "Three rules that make sastaspace possible: cheap to build, one command to live, open by default.",
};

export default function LabPage() {
  return (
    <div className={styles.wrap}>
      <TopNav />

      <section className={styles.section} style={{ borderTop: "none", paddingTop: 32 }}>
        <div className={styles.eyebrow}>the idea</div>
        <h1 style={{ fontSize: 48, lineHeight: 1.1, fontWeight: 500, letterSpacing: "-0.02em", margin: "0 0 18px", maxWidth: 820 }}>
          Not a portfolio. A lab.
        </h1>
        <p className={styles.lede}>
          Portfolios edit for wins. Labs show the whole bench. Sastaspace runs on three rules — the
          ones that make it possible to keep shipping small things without turning each one into a
          startup.
        </p>
        <div className={styles.principles} role="list">
          <div className={styles.principle} role="listitem">
            <div className={styles.principleNum}>01 / sasta</div>
            <h3>Cheap to build.</h3>
            <p>
              Boring tools. Shared infrastructure. New projects cost closer to zero than they do to
              a weekend brunch. The bill stays small so the imagination stays loud.
            </p>
          </div>
          <div className={styles.principle} role="listitem">
            <div className={styles.principleNum}>02 / shipped</div>
            <h3>One command to live.</h3>
            <p>
              Every experiment gets its own subdomain and goes from an idea to a working URL in the
              time it takes to name it. If it doesn't ship, it doesn't count.
            </p>
          </div>
          <div className={styles.principle} role="listitem">
            <div className={styles.principleNum}>03 / shared</div>
            <h3>Open by default.</h3>
            <p>
              Open URL, open source, open to being copied, forked, or improved on. The lab is on
              the internet so other people can find it — including me, six months from now.
            </p>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
