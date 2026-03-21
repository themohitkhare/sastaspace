// web/src/components/progress/site-screenshot.tsx
"use client"

import { motion } from "motion/react"

interface SiteScreenshotProps {
  screenshotBase64: string
  domain: string
}

export function SiteScreenshot({ screenshotBase64, domain }: SiteScreenshotProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="relative w-full max-w-sm rounded-xl overflow-hidden border border-border/50 shadow-lg"
    >
      <img
        src={`data:image/png;base64,${screenshotBase64}`}
        alt={`Current ${domain} website`}
        className="w-full object-cover object-top"
        style={{ filter: "saturate(0.3) brightness(0.85)", maxHeight: "200px" }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent" />
      <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between">
        <span className="text-xs text-white/80 font-medium">{domain} — before</span>
        <motion.span
          animate={{ opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="text-xs text-white/60"
        >
          transforming…
        </motion.span>
      </div>
    </motion.div>
  )
}
