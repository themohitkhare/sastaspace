// web/src/components/progress/progress-view.tsx
"use client";

import { useState, useEffect } from "react";
import { m } from "motion/react";
import { AlertCircle, RotateCcw, RefreshCw, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { AuroraBackground } from "@/components/ui/aurora-background";
import { LumaSpin } from "@/components/ui/luma-spin";
import { StepPills } from "@/components/progress/step-pills";
import { InsightCards } from "@/components/progress/insight-cards";
import { ColorSwatches } from "@/components/progress/color-swatches";
import { AutoPong } from "@/components/progress/auto-pong";
import type { RedesignState, RedesignTier } from "@/hooks/use-redesign";

// ETA in seconds by tier
const TIER_ETA_SECONDS: Record<RedesignTier, number> = {
  free: 120,
  premium: 300,
};

// Which step failed, for user-friendly error context
const STEP_FAILURE_LABELS: Record<string, string> = {
  connecting: "connecting to server",
  crawling: "crawling your website",
  discovering: "discovering pages",
  downloading: "downloading assets",
  analyzing: "analyzing content",
  redesigning: "AI redesign",
  deploying: "deploying the result",
};

function useCountdown(tier: RedesignTier, isActive: boolean) {
  const totalSeconds = TIER_ETA_SECONDS[tier];
  const [remaining, setRemaining] = useState(totalSeconds);

  useEffect(() => {
    if (!isActive) return;

    let elapsed = 0;
    const interval = setInterval(() => {
      elapsed += 1;
      setRemaining((prev) => Math.max(0, prev - 1));
    }, 1000);

    return () => {
      clearInterval(interval);
      // Suppress: elapsed used in interval callback
      void elapsed;
    };
  }, [isActive, totalSeconds]);

  return isActive ? remaining : totalSeconds;
}

function formatCountdown(seconds: number): string {
  if (seconds <= 0) return "Almost done...";
  if (seconds < 30) return "Almost done...";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

// Map step name → top-level progress bar value
const STEP_TO_PROGRESS: Record<string, number> = {
  connecting: 3,
  crawling: 25,
  redesigning: 65,
  deploying: 90,
  done: 100,
};

type ProgressViewState = Extract<RedesignState, { status: "progress" | "error" | "connecting" }>;
type ErrorState = Extract<RedesignState, { status: "error" }>;

function ErrorView({
  state,
  onRetry,
  onReset,
  lastStep,
}: {
  state: ErrorState;
  onRetry: (updatedPrompt?: string) => void;
  onReset?: () => void;
  lastStep?: string;
}) {
  const [retryPrompt, setRetryPrompt] = useState(state.prompt ?? "");
  const isNetworkError = Boolean(state.resumeJobId);
  const failedStepLabel = lastStep ? STEP_FAILURE_LABELS[lastStep] : undefined;

  const handleRetry = () => {
    onRetry(retryPrompt.trim() || undefined);
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <m.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="flex flex-col items-center gap-4 text-center w-full max-w-md"
      >
        <AlertCircle className="w-12 h-12 text-destructive" />
        <h2 className="font-heading text-[clamp(1.5rem,3vw,2rem)] text-foreground">
          Something went wrong
        </h2>

        {/* Show the original URL that was submitted */}
        {state.url && (
          <p className="text-sm text-muted-foreground font-mono bg-muted px-3 py-1.5 rounded-md">
            {state.url}
          </p>
        )}

        {/* Show which step failed */}
        {failedStepLabel && (
          <p className="text-sm text-muted-foreground">
            Failed during: <span className="font-medium text-foreground">{failedStepLabel}</span>
          </p>
        )}

        <p className="text-base text-muted-foreground max-w-sm">
          {state.message}
        </p>

        {/* Custom instructions textarea — shown for non-network errors */}
        {!isNetworkError && (
          <div className="w-full">
            <label
              htmlFor="retry-prompt"
              className="block text-sm font-medium text-muted-foreground text-left mb-1.5"
            >
              Custom instructions <span className="text-muted-foreground/60">(optional)</span>
            </label>
            <textarea
              id="retry-prompt"
              value={retryPrompt}
              onChange={(e) => setRetryPrompt(e.target.value)}
              placeholder="e.g. Make it dark theme, use a SaaS landing page layout..."
              rows={3}
              className="w-full rounded-md border border-border bg-muted/50 px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-accent/50 focus:border-accent resize-none"
            />
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <Button
            size="lg"
            onClick={handleRetry}
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
                Try again with {state.url ? new URL(state.url.startsWith("http") ? state.url : `https://${state.url}`).hostname : "this URL"}
              </>
            )}
          </Button>
          {onReset && (
            <Button
              size="lg"
              variant="outline"
              onClick={onReset}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Try a different URL
            </Button>
          )}
        </div>
      </m.div>
    </div>
  );
}

interface ProgressViewProps {
  state: ProgressViewState;
  onRetry: (updatedPrompt?: string) => void;
  onReset?: () => void;
  lastStep?: string;
}

export function ProgressView({ state, onRetry, onReset, lastStep }: ProgressViewProps) {
  // Hooks must be called unconditionally — derive tier before the early return
  const tierForCountdown: RedesignTier =
    state.status === "progress" ? state.tier : "free";
  const isActiveProgress = state.status === "progress" || state.status === "connecting";
  const remaining = useCountdown(tierForCountdown, isActiveProgress);

  // --- Error state ---
  if (state.status === "error") {
    return (
      <ErrorView
        state={state}
        onRetry={onRetry}
        onReset={onReset}
        lastStep={lastStep}
      />
    );
  }

  // --- Connecting / progress state ---
  const isConnecting = state.status === "connecting";
  const domain = isConnecting ? "" : state.domain;
  const currentStep = isConnecting ? "connecting" : state.currentStep;
  const siteColors = isConnecting ? [] : state.siteColors;
  const jobStatus = isConnecting ? "queued" : state.currentStep;
  const progressValue = STEP_TO_PROGRESS[currentStep] ?? 5;

  const STEP_LABELS: Record<string, string> = {
    connecting: "Connecting to server",
    crawling: "Crawling website content",
    analyzing: "Analyzing your website",
    designing: "Crafting your design system",
    selecting: "Selecting components",
    building: "Building your new site",
    reviewing: "Running quality checks",
    redesigning: "AI is redesigning your website",
    deploying: "Deploying the redesigned site",
    done: "Redesign complete",
  };
  const currentStepLabel = STEP_LABELS[currentStep] ?? "Processing";

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
      <div
        className="relative z-10 flex flex-col items-center gap-6 px-4 py-16 w-full max-w-md"
        role="status"
        aria-live="polite"
        aria-label={currentStepLabel}
      >
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
          <p className="text-xs text-muted-foreground mt-1 tabular-nums">
            {remaining < 30
              ? "Almost done..."
              : `Estimated time remaining: ${formatCountdown(remaining)}`}
          </p>
        </div>

        {/* Step pills */}
        <StepPills currentStatus={jobStatus} />

        {/* Rotating insight cards */}
        <InsightCards domain={domain} />

        {/* Color swatches — fade in when crawl data arrives */}
        <ColorSwatches colors={siteColors} />

        {/* Auto-play Pong while waiting */}
        <AutoPong className="mt-4" />
      </div>
    </AuroraBackground>
  );
}
