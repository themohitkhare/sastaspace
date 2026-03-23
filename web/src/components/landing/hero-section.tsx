"use client";

import React from "react";
import Link from "next/link";
import { m } from "motion/react";
import { FlickeringGrid } from "@/components/backgrounds/flickering-grid";
import { UrlInputForm } from "@/components/landing/url-input-form";
import type { RedesignTier, ModelProvider } from "@/hooks/use-redesign";

interface HeroSectionProps {
  onSubmit: (url: string, tier: RedesignTier, modelProvider: ModelProvider) => void;
}

export function HeroSection({ onSubmit }: HeroSectionProps) {
  return (
    <div className="relative min-h-screen flex flex-col justify-center overflow-hidden bg-background">
      <FlickeringGrid className="absolute inset-0 z-0" />
      <nav className="absolute top-0 left-0 right-0 z-20 flex items-center justify-between w-full max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 py-6">
        <span className="font-heading text-xl text-foreground">SastaSpace</span>
        <Link
          href="/pricing"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          Pricing
        </Link>
      </nav>
      <div className="relative z-10 w-full max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 py-24">
        <div className="max-w-2xl">
          <m.h1
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1, ease: "easeOut" }}
            className="font-heading text-[clamp(2.5rem,6vw,4.5rem)] leading-[1.08] text-foreground"
          >
            See your website{" "}
            <br className="hidden sm:block" />
            <span className="text-accent">reimagined</span>
          </m.h1>
          <m.p
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.2, ease: "easeOut" }}
            className="text-lg sm:text-xl text-muted-foreground font-sans mt-6 mb-10 max-w-lg"
          >
            Enter your URL and watch AI redesign your site in under a minute.
          </m.p>
          <m.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.3, ease: "easeOut" }}
          >
            <UrlInputForm onSubmit={onSubmit} />
          </m.div>
        </div>
      </div>
    </div>
  );
}
