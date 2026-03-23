"use client";

import { m } from "motion/react";

interface PageEntranceProps {
  children: React.ReactNode;
}

export function PageEntrance({ children }: PageEntranceProps) {
  return (
    <m.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      {children}
    </m.div>
  );
}
