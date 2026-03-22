// web/src/components/progress/progress-view.tsx
"use client";

import { m } from "motion/react";
import { AlertCircle, RotateCcw, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { AuroraBackground } from "@/components/ui/aurora-background";
import { LumaSpin } from "@/components/ui/luma-spin";
import { Counter } from "@/components/ui/animated-counter";
import { StepPills } from "@/components/progress/step-pills";
import { InsightCards } from "@/components/progress/insight-cards";
import { ColorSwatches } from "@/components/progress/color-swatches";
import type { RedesignState } from "@/hooks/use-redesign";

// Map step name → top-level progress bar value
const STEP_TO_PROGRESS: Record<string, number> = {
  connecting: 3,
  crawling: 25,
  redesigning: 65,
  deploying: 90,
  done: 100,
};

type ProgressViewState = Extract<RedesignState, { status: "progress" | "error" | "connecting" }>;

interface ProgressViewProps {
  state: ProgressViewState;
  onRetry: () => void;
}

export function ProgressView({ state, onRetry }: ProgressViewProps) {
  // --- Error state ---
  if (state.status === "error") {
    const isRateLimit =
      state.message.toLowerCase().includes("rate limit") ||
      state.message.toLowerCase().includes("limit");
    const isNetworkError = Boolean(state.resumeJobId);

    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <m.div
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
          <Button
            size="lg"
            onClick={onRetry}
            className="bg-accent text-accent-foreground hover:bg-accent/90"
          >
            {isNetworkError ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2" />
                Check status
              </>
            ) : (
              <>
                <RotateCcw className="w-4 h-4 mr-2" />
                Try again
              </>
            )}
          </Button>
        </m.div>
      </div>
    );
  }

  // --- Connecting / progress state ---
  const isConnecting = state.status === "connecting";
  const domain = isConnecting ? "" : state.domain;
  const currentStep = isConnecting ? "connecting" : state.currentStep;
  const siteColors = isConnecting ? [] : state.siteColors;
  const jobStatus = isConnecting ? "queued" : state.currentStep;

  const progressValue = STEP_TO_PROGRESS[currentStep] ?? 5;

  return (
    <AuroraBackground className="min-h-screen" showRadialGradient>
      {/* Top progress bar */}
      <div className="absolute top-0 left-0 right-0 z-10">
        <Progress
          value={progressValue}
          className="h-1 rounded-none bg-transparent"
          indicatorClassName="bg-accent transition-all duration-1000"
        />
      </div>

      {/* Centered content */}
      <div className="relative z-10 flex flex-col items-center gap-6 px-4 py-16 w-full max-w-md">
        {/* Spinner */}
        <LumaSpin />

        {/* Domain title */}
        <div className="text-center">
          {domain ? (
            <p className="font-heading text-lg font-medium text-foreground">
              Redesigning <span className="text-accent">{domain}</span>
            </p>
          ) : (
            <p className="font-heading text-lg font-medium text-foreground">Starting…</p>
          )}
          <p className="text-xs text-muted-foreground mt-1">
            AI redesigns typically take 2–3 minutes
          </p>
        </div>

        {/* Step pills */}
        <StepPills currentStatus={jobStatus} />

        {/* Rotating insight cards */}
        <InsightCards domain={domain} />

        {/* Color swatches — fade in when crawl data arrives */}
        <ColorSwatches colors={siteColors} />

        {/* Animated counter */}
        <div className="flex items-center gap-1.5 text-muted-foreground text-sm mt-2">
          <Counter
            start={12800}
            end={12847}
            duration={3}
            fontSize={14}
            className="text-foreground font-semibold"
          />
          <span>redesigns completed</span>
        </div>
      </div>
    </AuroraBackground>
  );
}
