"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { m, AnimatePresence } from "motion/react";
import { ExternalLink, Download, ArrowRight, RefreshCw } from "lucide-react";
import { NavHeader } from "@/components/ui/nav-header";
import { ContactForm } from "@/components/result/contact-form";
import { BeforeAfterSlider } from "@/components/result/before-after-slider";
import { ShareButtons } from "@/components/result/share-buttons";
import { QualityRating } from "@/components/result/quality-rating";
import { ProgressView } from "@/components/progress/progress-view";
import { SuccessCelebration } from "@/components/progress/success-celebration";
import { Footer } from "@/components/landing/footer";
import { getBackendUrl } from "@/lib/env";
import { subdomainToDomain } from "@/lib/url-utils";
import { useRedesign } from "@/hooks/use-redesign";

interface ResultViewProps {
  subdomain: string;
  tier?: string;
}

export function ResultView({ subdomain, tier }: ResultViewProps) {
  const domain = subdomainToDomain(subdomain);
  const originalUrl = `https://${domain}`;
  const backendUrl = getBackendUrl();
  // Iframe loads from backend directly (needs actual HTML content)
  const iframePreviewUrl = `${backendUrl}/${subdomain}/preview`;
  // User-facing links use frontend domain (proxied via Next.js rewrites)
  const previewUrl = `/${subdomain}/preview`;
  const downloadUrl = `/${subdomain}/index.html`;
  const shareUrl = typeof window !== "undefined"
    ? `${window.location.origin}/${subdomain}`
    : `/${subdomain}`;

  const { state, start, retry, reset } = useRedesign();
  const router = useRouter();
  const redirectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // When redesign completes, redirect to the new result page
  useEffect(() => {
    if (state.status === "done") {
      const tierParam = state.tier === "free" ? "?tier=express" : "";
      redirectTimerRef.current = setTimeout(() => {
        router.push(`/${state.subdomain}${tierParam}`);
      }, 1500);
      return () => {
        if (redirectTimerRef.current) clearTimeout(redirectTimerRef.current);
      };
    }
  }, [state, router]);

  function handleRedesignAgain() {
    start(originalUrl, "free", "gemini", "", true);
  }

  // Show progress view when redesign is in progress
  if (state.status === "connecting" || state.status === "progress" || state.status === "error") {
    return (
      <AnimatePresence mode="wait">
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
      </AnimatePresence>
    );
  }

  // Show celebration when done
  if (state.status === "done") {
    return (
      <m.div
        key="celebration"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
      >
        <SuccessCelebration domain={state.domain} />
      </m.div>
    );
  }

  // Default: show result view
  return (
    <m.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="min-h-screen flex flex-col items-center px-4"
    >
      <NavHeader />
      <div className="w-full max-w-4xl flex flex-col items-center pt-8">
        <p className="text-sm text-accent font-medium uppercase tracking-wide mb-3">
          Your Redesign
        </p>
        <h1 className="font-heading text-[clamp(1.75rem,5vw,3rem)] leading-[1.1] text-foreground text-center mb-2">
          {domain}
        </h1>
        <p className="text-muted-foreground text-center mb-8">
          Here&apos;s what your website could look like.
        </p>

        {/* Before/After comparison slider */}
        <BeforeAfterSlider originalUrl={originalUrl} redesignUrl={iframePreviewUrl} />

        {/* Action buttons */}
        <div className="mt-6 flex flex-col sm:flex-row items-center gap-3">
          <a
            href={previewUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 justify-center rounded-lg bg-accent text-accent-foreground text-base font-medium h-12 px-8 transition-all hover:bg-accent/90 active:translate-y-px"
          >
            Open Full Preview
            <ExternalLink className="w-4 h-4" />
          </a>
          <a
            href={downloadUrl}
            download={`${subdomain}-redesign.html`}
            className="inline-flex items-center gap-2 justify-center rounded-lg bg-secondary text-secondary-foreground text-sm font-medium h-11 px-6 transition-all hover:bg-secondary/80 active:translate-y-px"
          >
            <Download className="w-4 h-4" />
            Download HTML
          </a>
          <a
            href={originalUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground transition-colors"
          >
            View original
            <ExternalLink className="w-3.5 h-3.5" />
          </a>
          <button
            type="button"
            onClick={handleRedesignAgain}
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Redesign again
          </button>
        </div>

        {/* Social sharing buttons */}
        <div className="mt-6">
          <ShareButtons url={shareUrl} domain={domain} />
        </div>

        {/* Upgrade CTA for Express tier */}
        {tier === "express" && (
          <div className="text-center p-4 bg-accent/5 rounded-lg border border-accent/20 mt-6">
            <p className="text-sm text-muted-foreground">
              This was an <strong>Express</strong> preview.
              <a href="/pricing" className="text-accent hover:underline ml-1">Upgrade to Studio</a> for premium quality.
            </p>
          </div>
        )}

        {/* Quality rating — collect user feedback */}
        <div className="mt-10">
          <QualityRating subdomain={subdomain} />
        </div>

        {/* CTA section — lead generation */}
        <div className="mt-16 w-full max-w-2xl mx-auto text-center">
          <h2 className="font-heading text-2xl sm:text-3xl text-foreground mb-3">
            Love it? Let&apos;s make it real.
          </h2>
          <p className="text-muted-foreground mb-8 max-w-lg mx-auto">
            This is an AI-generated preview. Get a production-ready website with custom features, real content, and ongoing support.
          </p>
          <a
            href="#contact"
            className="inline-flex items-center gap-2 justify-center rounded-lg bg-accent text-accent-foreground text-base font-medium h-12 px-8 transition-all hover:bg-accent/90 active:translate-y-px"
          >
            Get in Touch
            <ArrowRight className="w-4 h-4" />
          </a>
        </div>

        {/* Contact form section */}
        <hr className="border-border w-full max-w-3xl mt-16" />
        <div id="contact" className="mt-16 w-full flex flex-col items-center pb-16">
          <ContactForm subdomain={subdomain} />
        </div>
      </div>
      <Footer />
    </m.div>
  );
}
