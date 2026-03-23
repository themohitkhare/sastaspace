"use client";

import Link from "next/link";
import { m } from "motion/react";
import { Check, X, ArrowLeft } from "lucide-react";
import { FlickeringGrid } from "@/components/backgrounds/flickering-grid";
import { Footer } from "@/components/landing/footer";

const TIERS = [
  {
    name: "Express",
    price: "$0",
    priceLabel: "Free",
    description: "Quick AI preview",
    cta: "Get Started Free",
    ctaHref: "/#url-input",
    highlighted: false,
    features: [
      { text: "3 redesigns per month", included: true },
      { text: "Basic AI quality", included: true },
      { text: "~2 min generation", included: true },
      { text: "Shareable preview link", included: true },
      { text: "Premium AI models", included: false },
      { text: "Priority support", included: false },
      { text: "Consultation hours", included: false },
    ],
  },
  {
    name: "Studio",
    price: "$99",
    priceLabel: "one-time",
    description: "Premium redesign",
    cta: "Upgrade to Studio",
    ctaHref: "/?tier=studio#url-input",
    highlighted: true,
    badge: "Most Popular",
    features: [
      { text: "Unlimited redesigns", included: true },
      { text: "Premium AI models", included: true },
      { text: "~5 min deep generation", included: true },
      { text: "Shareable preview link", included: true },
      { text: "Priority support", included: true },
      { text: "Consultation hours", included: false },
      { text: "Revision rounds", included: false },
    ],
  },
  {
    name: "Studio Pro",
    price: "$499",
    priceLabel: "one-time",
    description: "Full build package",
    cta: "Book Consultation",
    ctaHref: process.env.NEXT_PUBLIC_CALENDAR_URL || "mailto:hello@sastaspace.com?subject=Studio%20Pro%20Plan",
    highlighted: false,
    features: [
      { text: "Custom-built website from your AI redesign", included: true },
      { text: "2 hours of 1-on-1 consultation", included: true },
      { text: "1 round of revisions included", included: true },
      { text: "Delivered in 2 weeks", included: true },
      { text: "Source code handover", included: true },
      { text: "Priority support", included: true },
      { text: "Everything in Studio", included: true },
    ],
  },
] as const;

export function PricingContent() {
  return (
    <main className="relative min-h-screen bg-background overflow-hidden">
      <FlickeringGrid className="absolute inset-0 z-0 opacity-40" />
      <div className="relative z-10 w-full max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 py-24">
        <m.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
        >
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors mb-12"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>
        </m.div>

        <m.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.05, ease: "easeOut" }}
          className="text-center mb-16"
        >
          <h1 className="font-heading text-[clamp(2rem,5vw,3.5rem)] leading-[1.1] text-foreground">
            Simple, transparent pricing
          </h1>
          <p className="text-lg text-muted-foreground mt-4 max-w-xl mx-auto">
            Start free, upgrade when you need premium quality or hands-on help.
          </p>
        </m.div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 lg:gap-8">
          {TIERS.map((tier, index) => (
            <m.div
              key={tier.name}
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{
                duration: 0.4,
                delay: 0.15 + index * 0.1,
                ease: "easeOut",
              }}
              className={`relative flex flex-col rounded-xl border p-8 backdrop-blur-sm ${
                tier.highlighted
                  ? "border-accent ring-2 ring-accent/20 bg-card/90"
                  : "border-border bg-card/90"
              }`}
            >
              {tier.highlighted && "badge" in tier && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-accent text-accent-foreground text-xs font-medium px-3 py-1 rounded-full">
                  {tier.badge}
                </span>
              )}

              <div className="mb-6">
                <h2 className="font-heading text-2xl text-foreground">
                  {tier.name}
                </h2>
                <p className="text-sm text-muted-foreground mt-1">
                  {tier.description}
                </p>
              </div>

              <div className="mb-8">
                <span className="text-4xl font-heading text-foreground">
                  {tier.price}
                </span>
                {tier.priceLabel !== "Free" && (
                  <span className="text-sm text-muted-foreground ml-2">
                    {tier.priceLabel}
                  </span>
                )}
              </div>

              <ul className="space-y-3 mb-8 flex-1">
                {tier.features.map((feature) => (
                  <li
                    key={feature.text}
                    className="flex items-start gap-2.5 text-sm"
                  >
                    {feature.included ? (
                      <Check className="w-4 h-4 text-accent shrink-0 mt-0.5" />
                    ) : (
                      <X className="w-4 h-4 text-muted-foreground/40 shrink-0 mt-0.5" />
                    )}
                    <span
                      className={
                        feature.included
                          ? "text-foreground"
                          : "text-muted-foreground/50"
                      }
                    >
                      {feature.text}
                    </span>
                  </li>
                ))}
              </ul>

              <a
                href={tier.ctaHref}
                className={`inline-flex items-center justify-center rounded-lg text-sm font-medium h-11 px-6 transition-all active:translate-y-px ${
                  tier.highlighted
                    ? "bg-accent text-accent-foreground hover:bg-accent/90"
                    : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                }`}
              >
                {tier.cta}
              </a>
            </m.div>
          ))}
        </div>
      </div>
      <Footer />
    </main>
  );
}
