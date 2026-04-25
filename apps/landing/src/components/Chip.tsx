import styles from "./chip.module.css";

export type ChipVariant = "live" | "wip" | "paused" | "open source" | "archived";

const variantClass: Record<ChipVariant, string> = {
  live: styles.live,
  wip: styles.wip,
  paused: styles.paused,
  "open source": styles.oss,
  archived: styles.archived,
};

export function Chip({ variant }: { variant: ChipVariant }) {
  return <span className={`${styles.chip} ${variantClass[variant]}`}>{variant}</span>;
}
