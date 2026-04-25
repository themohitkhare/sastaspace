"use client";

import { useEffect, useState } from "react";
import { subscribePresence } from "@/lib/spacetime";
import styles from "./presence-pill.module.css";

export function PresencePill() {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => subscribePresence((c) => setCount(c)), []);

  if (count === null || count <= 0) return null;

  const label = count === 1 ? "1 in the lab" : `${count} in the lab`;

  return (
    <span className={styles.pill} title="people connected to sastaspace right now">
      <span className={styles.dot} aria-hidden="true" />
      {label}
    </span>
  );
}
