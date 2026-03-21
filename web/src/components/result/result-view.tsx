"use client";

import { motion } from "motion/react";
import { ExternalLink } from "lucide-react";

interface ResultViewProps {
  subdomain: string;
  isShareable?: boolean;
}

export function ResultView({ subdomain, isShareable }: ResultViewProps) {
  const domain = subdomain.replace(/-/g, ".");
  const originalUrl = `https://${domain}`;

  const headerText = isShareable
    ? `${domain} has been redesigned`
    : `Your new ${domain} is ready`;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="min-h-screen flex flex-col items-center px-4 pt-16"
    >
      <div className="w-full max-w-3xl flex flex-col items-center">
        <h1 className="text-[28px] sm:text-[40px] font-semibold leading-[1.1] text-foreground text-center mb-8">
          {headerText}
        </h1>

        <div className="relative w-full aspect-[4/3] sm:aspect-video rounded-xl overflow-hidden border border-border">
          <iframe
            src={`/${subdomain}/`}
            sandbox="allow-scripts"
            className="w-full h-full"
            title="Your redesigned site preview"
          />
          <div className="absolute inset-0 backdrop-blur-md bg-background/30 flex flex-col items-center justify-center gap-4">
            <a
              href={`/${subdomain}/`}
              className="inline-flex items-center justify-center rounded-lg bg-primary text-primary-foreground text-sm font-medium h-11 px-6 transition-all hover:bg-primary/80 active:translate-y-px"
            >
              Take me to the future
            </a>
          </div>
        </div>

        <a
          href={originalUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm text-muted-foreground underline underline-offset-4 mt-6 hover:text-foreground transition-colors"
        >
          View original site
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </div>
    </motion.div>
  );
}
