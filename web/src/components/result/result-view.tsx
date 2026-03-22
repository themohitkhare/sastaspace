"use client";

import { m } from "motion/react";
import { ExternalLink } from "lucide-react";
import { ContactForm } from "@/components/result/contact-form";

interface ResultViewProps {
  subdomain: string;
}

export function ResultView({ subdomain }: ResultViewProps) {
  const domain = subdomain.replace(/-/g, ".");
  const originalUrl = `https://${domain}`;
  const headerText = `${domain} has been redesigned`;
  const previewUrl = `/${subdomain}/preview`;

  return (
    <m.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className="min-h-screen flex flex-col items-center px-4 pt-24"
    >
      <div className="w-full max-w-4xl flex flex-col items-center">
        <h1 className="font-heading text-[clamp(1.75rem,5vw,3rem)] leading-[1.1] text-foreground text-center mb-8">
          {headerText}
        </h1>

        <div className="relative w-full aspect-[4/3] sm:aspect-video rounded-xl overflow-hidden border border-border">
          <iframe
            src={previewUrl}
            sandbox="allow-scripts"
            className="w-full h-full"
            title="Your redesigned site preview"
          />
          <div className="absolute inset-0 backdrop-blur-md bg-background/30 flex flex-col items-center justify-center gap-4">
            <a
              href={previewUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center justify-center rounded-lg bg-accent text-accent-foreground text-base font-medium h-12 px-8 transition-all hover:bg-accent/90 active:translate-y-px"
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

        {/* Contact form section — per D-01 */}
        <hr className="border-border w-full max-w-3xl mt-16" />
        <div className="mt-16 w-full flex flex-col items-center pb-16">
          <ContactForm subdomain={subdomain} />
        </div>
      </div>
    </m.div>
  );
}
