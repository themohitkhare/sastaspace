"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence, m } from "motion/react";
import { HeroSection } from "@/components/landing/hero-section";
import { TrustBadges } from "@/components/landing/trust-badges";
import { HowItWorks } from "@/components/landing/how-it-works";
import { FaqSection } from "@/components/landing/faq-section";
import { Footer } from "@/components/landing/footer";
import { ProgressView } from "@/components/progress/progress-view";
import { SuccessCelebration } from "@/components/progress/success-celebration";
import { useRedesign } from "@/hooks/use-redesign";

export function AppFlow() {
  const { state, start, retry, reset } = useRedesign();
  const router = useRouter();
  const redirectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Navigate to result page after 1.5s celebration delay
  useEffect(() => {
    if (state.status === "done") {
      // Clear ?job=&url= query params so back-navigation doesn't re-trigger polling
      if (typeof window !== "undefined" && window.location.search) {
        window.history.replaceState(null, "", window.location.pathname);
      }
      const tierParam = state.tier === "free" ? "?tier=express" : "";
      redirectTimerRef.current = setTimeout(() => {
        router.push(`/${state.subdomain}${tierParam}`);
      }, 1500);
      return () => {
        if (redirectTimerRef.current) clearTimeout(redirectTimerRef.current);
      };
    }
  }, [state, router]);

  const isConnecting = state.status === "connecting";

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
          <HeroSection onSubmit={start} isConnecting={isConnecting} />
          <section className="py-10 px-4">
            <TrustBadges />
          </section>
          <section className="py-16 px-4">
            <HowItWorks />
          </section>
          <section className="py-16 px-4">
            <FaqSection />
          </section>
          <Footer />
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
            onReset={reset}
            lastStep={state.status === "error" ? state.lastStep : undefined}
          />
        </m.div>
      )}

      {state.status === "done" && (
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
