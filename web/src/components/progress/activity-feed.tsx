// web/src/components/progress/activity-feed.tsx
"use client"

import { AnimatePresence, motion } from "motion/react"
import type { ActivityItem } from "@/hooks/use-redesign"

const AGENT_ICONS: Record<string, string> = {
  crawl_analyst:      "🔍",
  design_strategist:  "🎨",
  copywriter:         "✍️",
  component_selector: "🧩",
  html_generator:     "⚡",
  quality_reviewer:   "✓",
  normalizer:         "🔧",
}

interface ActivityFeedProps {
  activities: ActivityItem[]
}

export function ActivityFeed({ activities }: ActivityFeedProps) {
  if (activities.length === 0) return null

  return (
    <div className="flex flex-col gap-1.5 w-full max-w-sm">
      <AnimatePresence mode="popLayout" initial={false}>
        {[...activities].reverse().slice(0, 5).map((item) => (
          <motion.div
            key={item.id}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.3, ease: "easeOut" }}
            className="flex items-center gap-2 text-sm text-muted-foreground"
          >
            <span className="text-base leading-none w-5 text-center">
              {AGENT_ICONS[item.agent] ?? "→"}
            </span>
            <span>{item.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
