"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { submitRedesign, pollJobStatus } from "@/lib/sse-client";
import { extractDomain } from "@/lib/url-utils";
import { trackEvent } from "@/lib/analytics";

type StepState = {
  name: string;
  label: string;
  value: number;
  status: "pending" | "active" | "done";
};

export type RedesignTier = "free" | "premium";
export type ModelProvider = "claude" | "gemini";

export type RedesignState =
  | { status: "idle" }
  | { status: "connecting" }
  | {
      status: "progress";
      currentStep: string;
      domain: string;
      steps: StepState[];
      tier: RedesignTier;
      jobId: string;
      siteColors: string[];
      siteTitle: string;
      retryCount: number;
      jobCreatedAt: string;
    }
  | { status: "done"; subdomain: string; originalUrl: string; domain: string; tier: RedesignTier }
  | { status: "error"; message: string; url: string; resumeJobId?: string; lastStep?: string };

const STEPS = [
  { name: "crawling", label: (d: string) => `Analyzing ${d}` },
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  { name: "discovering", label: (_: string) => "Discovering internal pages" },
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  { name: "downloading", label: (_: string) => "Downloading site assets" },
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  { name: "analyzing", label: (_: string) => "Understanding the business" },
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  { name: "redesigning", label: (_: string) => "Redesigning your site with AI" },
  { name: "deploying", label: (d: string) => `Preparing your new ${d}` },
] as const;

function makeInitialSteps(domain: string): StepState[] {
  return STEPS.map((s) => ({
    name: s.name,
    label: s.label(domain),
    value: 0,
    status: "pending" as const,
  }));
}

// Map job status → (step name, progress %)
const STATUS_TO_STEP: Record<string, { stepName: string; progressValue: number }> = {
  queued: { stepName: "crawling", progressValue: 5 },
  crawling: { stepName: "crawling", progressValue: 15 },
  discovering: { stepName: "discovering", progressValue: 25 },
  downloading: { stepName: "downloading", progressValue: 35 },
  analyzing: { stepName: "analyzing", progressValue: 45 },
  redesigning: { stepName: "redesigning", progressValue: 65 },
  deploying: { stepName: "deploying", progressValue: 90 },
};

const STEP_NAMES: string[] = STEPS.map((s) => s.name);

const GENERIC_ERROR_MESSAGE =
  "We couldn't redesign that site right now. This can happen with very large or complex websites.";

const JOB_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes

export function useRedesign() {
  const [state, setState] = useState<RedesignState>({ status: "idle" });
  const abortRef = useRef<AbortController | null>(null);
  const lastUrlRef = useRef<string>("");
  const lastTierRef = useRef<RedesignTier>("free");
  const lastModelProviderRef = useRef<ModelProvider>("claude");
  const lastStepRef = useRef<string>("");

  const pollJob = useCallback(
    async (jobId: string, url: string, tier: RedesignTier, controller: AbortController) => {
      const domain = extractDomain(url);

      setState({
        status: "progress",
        currentStep: "crawling",
        domain,
        steps: makeInitialSteps(domain),
        tier,
        jobId,
        siteColors: [],
        siteTitle: "",
        retryCount: 0,
        jobCreatedAt: "",
      });

      try {
        for await (const job of pollJobStatus(jobId, controller.signal)) {
          if (controller.signal.aborted) return;

          if (job.status === "failed") {
            setState({
              status: "error",
              message: job.error || GENERIC_ERROR_MESSAGE,
              url,
              lastStep: lastStepRef.current,
            });
            return;
          }

          if (job.status === "done") {
            // Flash all steps to 100% for 800ms before transitioning
            const doneSteps = makeInitialSteps(domain).map((step) => ({
              ...step,
              value: 100,
              status: "done" as const,
            }));
            setState((prev) =>
              prev.status === "progress" ? { ...prev, currentStep: "done", steps: doneSteps } : prev
            );
            await new Promise((r) => setTimeout(r, 800));
            if (controller.signal.aborted) return;
            trackEvent("result_viewed", { subdomain: job.subdomain, domain, tier });
            setState({
              status: "done",
              subdomain: job.subdomain!,
              originalUrl: url,
              domain,
              tier,
            });
            return;
          }

          // Guard: job too old (only for in-progress jobs, not done/failed)
          if (job.created_at) {
            const ageMs = Date.now() - new Date(job.created_at).getTime();
            if (ageMs > JOB_TIMEOUT_MS) {
              setState({
                status: "error",
                message:
                  "This is taking longer than expected. Please check back in a few minutes.",
                url,
                lastStep: lastStepRef.current,
              });
              return;
            }
          }

          // In-progress update
          const { stepName, progressValue } =
            STATUS_TO_STEP[job.status] ?? STATUS_TO_STEP.queued;
          lastStepRef.current = stepName;
          const stepIndex = STEP_NAMES.indexOf(stepName);
          const updatedSteps = makeInitialSteps(domain).map((step, i) => {
            if (i < stepIndex) return { ...step, value: 100, status: "done" as const };
            if (i === stepIndex)
              return { ...step, value: progressValue, status: "active" as const };
            return step;
          });

          setState({
            status: "progress",
            currentStep: stepName,
            domain,
            steps: updatedSteps,
            tier,
            jobId,
            siteColors: job.site_colors ?? [],
            siteTitle: job.site_title ?? "",
            retryCount: 0,
            jobCreatedAt: job.created_at ?? "",
          });
        }
      } catch (e) {
        if (controller.signal.aborted) return;
        const isPollFailed = e instanceof Error && e.message === "POLL_FAILED";
        setState({
          status: "error",
          message: isPollFailed
            ? "Having trouble connecting. Your redesign may still be in progress — check back in a few minutes."
            : GENERIC_ERROR_MESSAGE,
          url,
          resumeJobId: isPollFailed ? jobId : undefined,
          lastStep: lastStepRef.current,
        });
      }
    },
    []
  );

  const start = useCallback(
    async (url: string, tier: RedesignTier = "free", modelProvider: ModelProvider = "claude") => {
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      lastUrlRef.current = url;
      lastTierRef.current = tier;
      lastModelProviderRef.current = modelProvider;

      setState({ status: "connecting" });
      trackEvent("redesign_started", { url, tier, modelProvider });

      try {
        const jobId = await submitRedesign(url, tier, modelProvider, controller.signal);
        if (controller.signal.aborted) return;

        // Persist job ID + original URL for page-refresh reconnection
        if (typeof window !== "undefined") {
          const params = new URLSearchParams(window.location.search);
          params.set("job", jobId);
          params.set("url", url);
          window.history.replaceState(
            null,
            "",
            `${window.location.pathname}?${params.toString()}`
          );
        }

        await pollJob(jobId, url, tier, controller);
      } catch {
        if (controller.signal.aborted) return;
        setState({ status: "error", message: GENERIC_ERROR_MESSAGE, url, lastStep: lastStepRef.current });
      }
    },
    [pollJob]
  );

  const retry = useCallback(() => {
    if (state.status !== "error") return;
    if (state.resumeJobId) {
      // Network failure: resume polling the existing job
      const controller = new AbortController();
      abortRef.current = controller;
      pollJob(state.resumeJobId, state.url, lastTierRef.current, controller);
    } else {
      start(state.url, lastTierRef.current, lastModelProviderRef.current);
    }
  }, [state, start, pollJob]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState({ status: "idle" });
  }, []);

  // On mount: if ?job= present in URL, resume polling without re-submitting
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const jobId = params.get("job");
    if (!jobId) return;

    const controller = new AbortController();
    abortRef.current = controller;
    const url = params.get("url") || lastUrlRef.current || "";
    if (url) lastUrlRef.current = url;
    pollJob(jobId, url, lastTierRef.current, controller);

    return () => {
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return { state, start, retry, reset };
}
