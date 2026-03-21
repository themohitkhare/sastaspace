"use client";

import React from "react";
import { motion } from "motion/react";
import { Spotlight } from "@/components/backgrounds/spotlight";
import { UrlInputForm } from "@/components/landing/url-input-form";

interface HeroSectionProps {
  onSubmit: (url: string) => void;
}

export function HeroSection({ onSubmit }: HeroSectionProps) {
  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden bg-background">
      <Spotlight />
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2, ease: "easeOut" }}
        className="relative z-10 flex flex-col items-center text-center px-4 pt-16 pb-12"
      >
        <div className="max-w-2xl flex flex-col items-center">
          <h1 className="text-[28px] sm:text-[40px] font-semibold leading-[1.1] text-foreground mb-4">
            See your website reimagined
          </h1>
          <p className="text-base text-muted-foreground mb-8 max-w-lg">
            Enter your URL and watch AI redesign your site in under a minute.
          </p>
          <UrlInputForm onSubmit={onSubmit} />
        </div>
      </motion.div>
    </div>
  );
}
