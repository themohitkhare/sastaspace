"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, m } from "motion/react";
import { HeroSection } from "@/components/landing/hero-section";
import { HowItWorks } from "@/components/landing/how-it-works";
import { ProgressView } from "@/components/progress/progress-view";
import { useRedesign } from "@/hooks/use-redesign";

export function AppFlow() {
  const { state, start, retry } = useRedesign();
  const router = useRouter();

  // Navigate to result page when done
  useEffect(() => {
    if (state.status === "done") {
      router.replace(`/${state.subdomain}`);
    }
  }, [state, router]);

  return (
    <AnimatePresence mode="wait">
      {state.status === "idle" && (
        <m.div
          key="landing"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
        >
          <HeroSection onSubmit={start} />
          <section className="py-12 px-4">
            <HowItWorks />
          </section>
        </m.div>
      )}

      {(state.status === "connecting" ||
        state.status === "progress" ||
        state.status === "error") && (
        <m.div
          key="progress"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
        >
          <ProgressView
            state={state}
            onRetry={retry}
          />
        </m.div>
      )}
    </AnimatePresence>
  );
}
