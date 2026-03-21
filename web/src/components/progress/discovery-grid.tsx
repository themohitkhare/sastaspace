// web/src/components/progress/discovery-grid.tsx
"use client"

import { motion } from "motion/react"
import type { DiscoveryItem } from "@/hooks/use-redesign"

interface DiscoveryGridProps {
  items: DiscoveryItem[]
}

export function DiscoveryGrid({ items }: DiscoveryGridProps) {
  if (items.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="grid grid-cols-2 gap-2 w-full max-w-sm"
    >
      {items.map((item, i) => (
        <motion.div
          key={item.label}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: i * 0.08, duration: 0.3 }}
          className="rounded-lg border border-border/50 bg-muted/30 px-3 py-2"
        >
          <p className="text-xs text-muted-foreground">{item.label}</p>
          <p className="text-sm font-medium text-foreground truncate">{item.value}</p>
        </motion.div>
      ))}
    </motion.div>
  )
}
