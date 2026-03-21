"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { submitRedesign, streamJobStatus } from "@/lib/sse-client";
import { extractDomain } from "@/lib/url-utils";

type StepState = {
  name: string;
  label: string;
  value: number;
  status: "pending" | "active" | "done";
};

export type ActivityItem = { id: string; agent: string; message: string; timestamp: number };
export type DiscoveryItem = { label: string; value: string };
export type RedesignTier = "standard" | "premium";

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
      activities: ActivityItem[];
      discoveryItems: DiscoveryItem[];
      screenshot?: string;
    }
  | { status: "done"; subdomain: string; originalUrl: string; domain: string; tier: RedesignTier }
  | { status: "error"; message: string; url: string };

const STEPS = [
  { name: "crawling", label: (d: string) => `Analyzing ${d}` },
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  { name: "redesigning", label: (_d: string) => "Redesigning your site with AI" },
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

const STEP_INTERMEDIATE_VALUES: Record<string, number> = {
  crawling: 70,
  redesigning: 50,
  deploying: 60,
};

export function useRedesign() {
  const [state, setState] = useState<RedesignState>({ status: "idle" });
  const abortRef = useRef<AbortController | null>(null);
  const lastUrlRef = useRef<string>("");
  const lastTierRef = useRef<RedesignTier>("standard");

  const streamJob = useCallback(
    async (jobId: string, url: string, tier: RedesignTier, controller: AbortController) => {
      const domain = extractDomain(url);
      const initialSteps = makeInitialSteps(domain);

      setState({
        status: "progress",
        currentStep: "crawling",
        domain,
        steps: initialSteps,
        tier,
        jobId,
        activities: [],
        discoveryItems: [],
        screenshot: undefined,
      });

      try {
        for await (const event of streamJobStatus(jobId, controller.signal)) {
          if (controller.signal.aborted) return;

          const stepNames = STEPS.map((s) => s.name);

          if (
            event.event === "crawling" ||
            event.event === "redesigning" ||
            event.event === "deploying"
          ) {
            const eventIndex = stepNames.indexOf(event.event);
            const updatedSteps = makeInitialSteps(domain).map((step, i) => {
              if (i < eventIndex) {
                return { ...step, value: 100, status: "done" as const };
              }
              if (i === eventIndex) {
                return {
                  ...step,
                  value: STEP_INTERMEDIATE_VALUES[event.event] ?? 50,
                  status: "active" as const,
                };
              }
              return step;
            });

            setState({
              status: "progress",
              currentStep: event.event,
              domain,
              steps: updatedSteps,
              tier,
              jobId,
              activities: [],
              discoveryItems: [],
              screenshot: undefined,
            });
          } else if (event.event === "done") {
            // Set all steps to done
            const doneSteps = makeInitialSteps(domain).map((step) => ({
              ...step,
              value: 100,
              status: "done" as const,
            }));

            setState({
              status: "progress",
              currentStep: "done",
              domain,
              steps: doneSteps,
              tier,
              jobId,
              activities: [],
              discoveryItems: [],
              screenshot: undefined,
            });

            // Pause 800ms before transitioning to done state
            await new Promise((r) => setTimeout(r, 800));

            if (controller.signal.aborted) return;

            setState({
              status: "done",
              subdomain: event.data.subdomain as string,
              originalUrl: url,
              domain,
              tier,
            });
          } else if (event.event === "error") {
            setState({
              status: "error",
              message: event.data.error as string,
              url,
            });
          }
        }
      } catch {
        if (controller.signal.aborted) return;
        setState({
          status: "error",
          message:
            "We couldn't redesign that site right now. This can happen with very large or complex websites.",
          url,
        });
      }
    },
    []
  );

  const start = useCallback(
    async (url: string, tier: RedesignTier = "standard") => {
      // Abort any existing connection
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      lastUrlRef.current = url;
      lastTierRef.current = tier;

      setState({ status: "connecting" });

      try {
        const jobId = await submitRedesign(url, tier, controller.signal);
        if (controller.signal.aborted) return;

        // Push job_id to URL for reconnection support
        if (typeof window !== "undefined") {
          const params = new URLSearchParams(window.location.search);
          params.set("job", jobId);
          const newUrl = `${window.location.pathname}?${params.toString()}`;
          window.history.replaceState(null, "", newUrl);
        }

        await streamJob(jobId, url, tier, controller);
      } catch {
        if (controller.signal.aborted) return;
        setState({
          status: "error",
          message:
            "We couldn't redesign that site right now. This can happen with very large or complex websites.",
          url,
        });
      }
    },
    [streamJob]
  );

  const retry = useCallback(() => {
    if (state.status === "error") {
      start(state.url, lastTierRef.current);
    }
  }, [state, start]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState({ status: "idle" });
  }, []);

  // On mount: reconnect if ?job= param is present in URL
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const jobId = params.get("job");
    if (!jobId) return;

    const controller = new AbortController();
    abortRef.current = controller;
    // We don't have the original URL, use empty string as placeholder
    const url = lastUrlRef.current || "";
    streamJob(jobId, url, lastTierRef.current, controller);

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
