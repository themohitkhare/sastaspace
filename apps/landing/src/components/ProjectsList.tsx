import { Chip, type ChipVariant } from "@/components/Chip";
import { PROJECTS, type Project } from "@/lib/projects";
import styles from "@/app/landing.module.css";

const KNOWN_STATUSES: readonly ChipVariant[] = [
  "live",
  "wip",
  "paused",
  "open source",
  "archived",
];

function asChipVariant(status: string): ChipVariant {
  return (KNOWN_STATUSES as readonly string[]).includes(status)
    ? (status as ChipVariant)
    : "wip";
}

export function ProjectsList() {
  if (PROJECTS.length === 0) {
    return (
      <div className={styles.emptyState}>
        <p>The workshop&apos;s quiet today. Come back soon.</p>
      </div>
    );
  }

  return (
    <div className={styles.grid}>
      {PROJECTS.map((p: Project) => (
        <a key={p.slug} className={styles.card} href={p.url}>
          <div className={styles.cardSlug}>{slugDomain(p.url)}</div>
          <h3>{p.title}</h3>
          <p>{p.blurb}</p>
          <div className={styles.cardMeta}>
            <Chip variant={asChipVariant(p.status)} />
            <div className={styles.tags}>
              {p.tags.map((t) => (
                <span key={t} className={styles.tag}>{t}</span>
              ))}
            </div>
          </div>
        </a>
      ))}
    </div>
  );
}

function slugDomain(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}
