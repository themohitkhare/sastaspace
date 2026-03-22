// web/src/components/progress/color-swatches.tsx
"use client";

import { AnimatePresence, motion } from "motion/react";

interface ColorSwatchesProps {
  colors: string[];
}

export function ColorSwatches({ colors }: ColorSwatchesProps) {
  if (!colors.length) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="flex flex-col items-center gap-2"
      >
        <div className="flex items-center gap-2">
          {colors.slice(0, 5).map((color, i) => (
            <div
              key={i}
              className="w-5 h-5 rounded-full border border-border/30 shadow-sm"
              style={{ backgroundColor: color }}
              title={color}
            />
          ))}
        </div>
        <p className="text-xs text-muted-foreground">Your brand colors</p>
      </motion.div>
    </AnimatePresence>
  );
}
