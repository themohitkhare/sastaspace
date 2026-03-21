"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { streamRedesign } from "@/lib/sse-client";
import { extractDomain } from "@/lib/url-utils";

type StepState = {
  name: string;
  label: string;
  value: number;
  status: "pending" | "active" | "done";
};

export type RedesignTier = "standard" | "premium";

export type RedesignState =
  | { status: "idle" }
  | { status: "connecting" }
  | { status: "progress"; currentStep: string; domain: string; steps: StepState[]; tier: RedesignTier }
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

  const start = useCallback(async (url: string, tier: RedesignTier = "standard") => {
    // Abort any existing connection
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    lastUrlRef.current = url;
    lastTierRef.current = tier;

    const domain = extractDomain(url);

    setState({ status: "connecting" });

    const initialSteps = makeInitialSteps(domain);
    setState({
      status: "progress",
      currentStep: "crawling",
      domain,
      steps: initialSteps,
      tier,
    });

    try {
      for await (const event of streamRedesign(url, process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080", controller.signal, tier)) {
        if (controller.signal.aborted) return;

        const stepNames = STEPS.map((s) => s.name);

        if (event.event === "crawling" || event.event === "redesigning" || event.event === "deploying") {
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
  }, []);

  const retry = useCallback(() => {
    if (state.status === "error") {
      start(state.url, lastTierRef.current);
    }
  }, [state, start]);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setState({ status: "idle" });
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  return { state, start, retry, reset };
}
