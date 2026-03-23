"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, m } from "motion/react";
import { HeroSection } from "@/components/landing/hero-section";
import { HowItWorks } from "@/components/landing/how-it-works";
import { FaqSection } from "@/components/landing/faq-section";
import { ProgressView } from "@/components/progress/progress-view";
import { SuccessCelebration } from "@/components/progress/success-celebration";
import { useRedesign } from "@/hooks/use-redesign";

export function AppFlow() {
  const { state, start, retry } = useRedesign();
  const router = useRouter();
  const [celebrating, setCelebrating] = useState(false);

  // Show celebration for 1.5s, then navigate to result page
  useEffect(() => {
    if (state.status === "done") {
      setCelebrating(true);
      const timer = setTimeout(() => {
        router.replace(`/${state.subdomain}`);
      }, 1500);
      return () => clearTimeout(timer);
    }
    setCelebrating(false);
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
          <section className="py-16 px-4">
            <HowItWorks />
          </section>
          <section className="py-16 px-4">
            <FaqSection />
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

      {state.status === "done" && celebrating && (
        <m.div
          key="celebration"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
        >
          <SuccessCelebration domain={state.domain} />
        </m.div>
      )}
    </AnimatePresence>
  );
}
