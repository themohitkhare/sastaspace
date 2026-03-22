// web/src/components/progress/step-pills.tsx
"use client";

import { cn } from "@/lib/utils";

type PillStep = {
  key: string;
  label: string;
  activeStatuses: string[];
};

const PILL_STEPS: PillStep[] = [
  { key: "analyzing", label: "Analyzing", activeStatuses: ["queued", "crawling"] },
  { key: "designing", label: "Designing", activeStatuses: ["redesigning"] },
  { key: "building", label: "Building", activeStatuses: ["deploying", "done"] },
];

interface StepPillsProps {
  currentStatus: string;
}

export function StepPills({ currentStatus }: StepPillsProps) {
  const activeIndex = PILL_STEPS.findIndex((p) =>
    p.activeStatuses.includes(currentStatus)
  );

  return (
    <div className="flex items-center gap-3">
      {PILL_STEPS.map((pill, i) => {
        const isDone = activeIndex > i;
        const isActive = activeIndex === i;
        return (
          <div
            key={pill.key}
            className={cn(
              "flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-300",
              isActive && "bg-accent text-accent-foreground",
              isDone && "bg-accent/20 text-accent",
              !isActive && !isDone && "bg-secondary text-muted-foreground"
            )}
          >
            <span
              className={cn(
                "w-1.5 h-1.5 rounded-full",
                isActive && "bg-accent-foreground",
                isDone && "bg-accent",
                !isActive && !isDone && "bg-muted-foreground/40"
              )}
            />
            {pill.label}
          </div>
        );
      })}
    </div>
  );
}
