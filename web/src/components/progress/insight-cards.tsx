// web/src/components/progress/insight-cards.tsx
"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, m } from "motion/react";

const TRACK_1 = [
  "Visiting {domain}…",
  "Downloading {domain} assets and images",
  "Reading your business copy",
  "Identifying your target audience",
  "Mapping your customer journey",
  "Analyzing your conversion funnel",
  "Benchmarking against your industry",
  "Understanding what makes you unique",
];

const TRACK_2 = [
  "Designing a layout built for conversions",
  "Writing copy that speaks to your customers",
  "Crafting your hero for maximum impact",
  "Selecting typography that fits your brand",
  "Tuning your color palette",
  "Building mobile-first components",
  "Adding micro-animations for delight",
  "Finalizing your redesign…",
];

// Track switches at 45s
const TRACK_SWITCH_MS = 45_000;
// Message rotates every 4s
const MESSAGE_INTERVAL_MS = 4_000;

interface InsightCardsProps {
  domain: string;
}

export function InsightCards({ domain }: InsightCardsProps) {
  const [elapsedMs, setElapsedMs] = useState(0);

  useEffect(() => {
    const id = setInterval(() => {
      setElapsedMs((prev) => prev + 1000);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const track = elapsedMs < TRACK_SWITCH_MS ? TRACK_1 : TRACK_2;
  const messageIndex = Math.floor(elapsedMs / MESSAGE_INTERVAL_MS) % track.length;
  const rawMessage = track[messageIndex];
  const message = rawMessage.replace(/\{domain\}/g, domain || "your site");

  return (
    <div className="w-full max-w-sm rounded-xl border border-border/40 bg-background/30 backdrop-blur-sm px-5 py-4 min-h-[64px] flex items-center justify-center" style={{ boxShadow: "var(--shadow-sm)" }}>
      <AnimatePresence mode="wait">
        <m.p
          key={`${messageIndex}-${elapsedMs < TRACK_SWITCH_MS ? 0 : 1}`}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.4 }}
          className="text-sm text-center text-foreground/80"
        >
          {message}
        </m.p>
      </AnimatePresence>
    </div>
  );
}
