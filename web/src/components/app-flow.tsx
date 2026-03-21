"use client";

import { useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, motion } from "motion/react";
import { HeroSection } from "@/components/landing/hero-section";
import { HowItWorks } from "@/components/landing/how-it-works";
import { ProgressView } from "@/components/progress/progress-view";
import { useRedesign } from "@/hooks/use-redesign";

export function AppFlow() {
  const { state, start, retry, reset } = useRedesign();
  const router = useRouter();

  const handleSubmit = useCallback(
    (url: string) => {
      start(url);
    },
    [start]
  );

  const handleRetry = useCallback(() => {
    retry();
  }, [retry]);

  const handleReset = useCallback(() => {
    reset();
  }, [reset]);

  // Navigate to result page when done
  useEffect(() => {
    if (state.status === "done") {
      router.push(`/${state.subdomain}`);
    }
  }, [state, router]);

  return (
    <AnimatePresence mode="wait">
      {state.status === "idle" && (
        <motion.div
          key="landing"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
        >
          <HeroSection onSubmit={handleSubmit} />
          <section className="py-12 px-4">
            <HowItWorks />
          </section>
        </motion.div>
      )}

      {(state.status === "connecting" ||
        state.status === "progress" ||
        state.status === "error") && (
        <motion.div
          key="progress"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -20 }}
          transition={{ duration: 0.3, ease: "easeInOut" }}
        >
          <ProgressView
            state={state}
            onRetry={handleRetry}
            onReset={handleReset}
          />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
