import { TopNav } from "@/components/TopNav";
import { Footer } from "@/components/Footer";
import { ProjectsList } from "@/components/ProjectsList";
import styles from "../landing.module.css";

export const metadata = {
  title: "projects — sastaspace",
  description: "What's on the bench: the small things being built in the lab right now.",
};

export default function ProjectsPage() {
  return (
    <div className={styles.wrap}>
      <TopNav />

      <section className={styles.section} style={{ borderTop: "none", paddingTop: 32 }}>
        <div className={styles.projectsHeader}>
          <div>
            <div className={styles.eyebrow}>projects</div>
            <h1 style={{ fontSize: 48, lineHeight: 1.1, fontWeight: 500, letterSpacing: "-0.02em", margin: 0 }}>
              What's on the bench.
            </h1>
          </div>
        </div>
        <ProjectsList />
      </section>

      <Footer />
    </div>
  );
}
