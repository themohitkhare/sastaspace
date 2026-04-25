import { TopNav } from "@/components/TopNav";
import { Footer } from "@/components/Footer";
import styles from "../landing.module.css";

export const metadata = {
  title: "about — sastaspace",
  description: "Mohit Khare: software engineer in Bengaluru, runs sastaspace on the side.",
};

export default function AboutPage() {
  return (
    <div className={styles.wrap}>
      <TopNav />

      <section className={styles.section} style={{ borderTop: "none", paddingTop: 32 }}>
        <div className={styles.about}>
          <div className={styles.aboutLeft}>
            <div className={styles.eyebrow}>about</div>
            <h1 style={{ fontSize: 42, lineHeight: 1.1, fontWeight: 500, letterSpacing: "-0.015em", margin: "0 0 10px" }}>
              Hi — I'm Mohit.
            </h1>
          </div>
          <div className={styles.aboutRight}>
            <p>
              I'm a software engineer in Bengaluru. I spend my days on the unglamorous end of
              software — making slow things fast, fragile things dependable, complicated things
              small. I like boring tools that age well.
            </p>
            <p>
              Sastaspace is the other half. It's where I build what I want to build — without
              asking anyone for a roadmap — and put it on the internet for whoever might want it.
              Some things here will get polished. Some will stay half-built forever. All of them
              are out in the open.
            </p>
            <p>
              If any of this is interesting, the best way to follow along is to bookmark{" "}
              <a href="https://notes.sastaspace.com">the notes</a>. I'm also on{" "}
              <a href="https://github.com/themohitkhare">GitHub</a> and{" "}
              <a href="https://www.linkedin.com/in/themohitkhare">LinkedIn</a>.
            </p>
            <div className={styles.cardCompact}>
              <div className={styles.cardCompactLabel}>the lab, in one line</div>
              <dl>
                <div className={styles.drow}>
                  <dt>Run by</dt>
                  <dd>one person</dd>
                </div>
                <div className={styles.drow}>
                  <dt>Budget</dt>
                  <dd>sasta — close to ₹0</dd>
                </div>
                <div className={styles.drow}>
                  <dt>Roadmap</dt>
                  <dd>none on purpose</dd>
                </div>
                <div className={styles.drow}>
                  <dt>Default state</dt>
                  <dd>open to the public</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
