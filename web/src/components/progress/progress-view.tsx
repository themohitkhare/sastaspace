"use client";

import { AnimatePresence, motion } from "motion/react";
import { AlertCircle, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { StepIndicator } from "@/components/progress/step-indicator";
import { ActivityFeed } from "@/components/progress/activity-feed";
import { DiscoveryGrid } from "@/components/progress/discovery-grid";
import type { RedesignState } from "@/hooks/use-redesign";

const STEP_LABELS: Record<string, (domain: string) => string> = {
  crawling: (d) => `Analyzing ${d}`,
  redesigning: () => "Redesigning your site with AI",
  deploying: (d) => `Preparing your new ${d}`,
  done: () => "Your redesign is ready!",
};

interface ProgressViewProps {
  state: RedesignState & { status: "progress" | "error" | "connecting" };
  onRetry: () => void;
  onReset: () => void;
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function ProgressView({ state, onRetry, onReset }: ProgressViewProps) {
  if (state.status === "error") {
    const isRateLimit =
      state.message.toLowerCase().includes("rate limit") ||
      state.message.toLowerCase().includes("limit");

    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
          className="flex flex-col items-center gap-4 text-center"
        >
          <AlertCircle className="w-12 h-12 text-destructive" />
          <h2 className="font-heading text-[clamp(1.5rem,3vw,2rem)] text-foreground">
            Something went wrong
          </h2>
          <p className="text-base text-muted-foreground max-w-sm">
            {isRateLimit
              ? "You've reached the limit. Please try again in an hour."
              : state.message}
          </p>
          <Button size="lg" onClick={onRetry} className="bg-accent text-accent-foreground hover:bg-accent/90">
            <RotateCcw className="w-4 h-4 mr-2" />
            Try again
          </Button>
        </motion.div>
      </div>
    );
  }

  // Connecting or progress state
  const isConnecting = state.status === "connecting";
  const domain = isConnecting ? "" : state.domain;
  const currentStep = isConnecting ? "connecting" : state.currentStep;
  const steps = isConnecting
    ? [
        { name: "crawling", label: "Analyzing...", value: 0, status: "pending" as const },
        { name: "redesigning", label: "Redesigning...", value: 0, status: "pending" as const },
        { name: "deploying", label: "Preparing...", value: 0, status: "pending" as const },
      ]
    : state.steps;

  const statusLabel = isConnecting
    ? "Connecting..."
    : STEP_LABELS[currentStep]?.(domain) ?? "Working...";

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-md flex flex-col gap-8">
        <AnimatePresence mode="wait">
          <motion.p
            key={currentStep}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="font-heading text-lg font-medium text-foreground text-center"
          >
            {statusLabel}
          </motion.p>
        </AnimatePresence>
        {/* Time expectation — shown immediately, reframes wait as quality signal */}
        <p className="text-xs text-muted-foreground text-center">
          AI redesigns typically take 2–3 minutes. Real work happening here.
        </p>

        {/* Discovery grid — appears after crawl completes */}
        {!isConnecting && <DiscoveryGrid items={state.discoveryItems} />}

        <div className="flex flex-col gap-4">
          {steps.map((step) => (
            <StepIndicator
              key={step.name}
              label={step.label}
              value={step.value}
              status={step.status}
            />
          ))}
        </div>

        {/* Live agent activity feed */}
        {!isConnecting && <ActivityFeed activities={state.activities} />}
      </div>
    </div>
  );
}
