"use client";

import Link from "next/link";
import { m } from "motion/react";
import { Check, X, ArrowLeft, ChevronDown } from "lucide-react";
import { useState } from "react";
import { FlickeringGrid } from "@/components/backgrounds/flickering-grid";
import { NavHeader } from "@/components/ui/nav-header";
import { Footer } from "@/components/landing/footer";

const TIERS = [
  {
    name: "Pro",
    price: "$19",
    priceLabel: "/mo",
    description: "Hosted Web UI",
    cta: "Start Pro Trial",
    ctaHref: "/#url-input?tier=studio",
    highlighted: true,
    badge: "Most Popular",
    features: [
      { text: "No API key needed", included: true },
      { text: "Hosted previews", included: true },
      { text: "Custom domains", included: true },
      { text: "Priority support", included: true },
      { text: "Remove badge option", included: true },
    ],
  },
  {
    name: "Agency",
    price: "$99",
    priceLabel: "/mo",
    description: "Scale Your Business",
    cta: "Book a Demo",
    ctaHref:
      process.env.NEXT_PUBLIC_CALENDAR_URL ||
      "mailto:hello@sastaspace.com?subject=Agency%20Plan%20Demo",
    highlighted: false,
    features: [
      { text: "Everything in Pro, plus:", included: true, isSectionLabel: true },
      { text: "Bulk redesigns (50/mo)", included: true },
      { text: "White-label output", included: true },
      { text: "Client handoff tools", included: true },
      { text: "2 consultation hours/mo", included: true },
      { text: "Dedicated support", included: true },
    ],
  },
  {
    name: "Enterprise",
    price: "Custom",
    priceLabel: "",
    description: "Your Infrastructure",
    cta: "Contact Sales",
    ctaHref: "mailto:hello@sastaspace.com?subject=Enterprise%20Plan",
    highlighted: false,
    features: [
      { text: "Everything in Agency, plus:", included: true, isSectionLabel: true },
      { text: "Self-hosted deployment", included: true },
      { text: "SSO & team management", included: true },
      { text: "Custom integrations", included: true },
      { text: "SLA guarantee", included: true },
      { text: "Dedicated account manager", included: true },
    ],
  },
] as const;

const PRICING_FAQS = [
  {
    question: "Is there a free option?",
    answer:
      "The open-source CLI is free forever — bring your own Anthropic API key (~$0.10/redesign). The hosted plans below add convenience, previews, and scale.",
  },
  {
    question: "Can I remove the 'Redesigned by SastaSpace' badge?",
    answer: "Agency plan includes white-label output with no attribution.",
  },
] as const;

function FaqItem({ question, answer }: { question: string; answer: string }) {
  const [open, setOpen] = useState(false);
  return (
    <button
      onClick={() => setOpen(!open)}
      className="w-full text-left border border-border rounded-lg p-5 backdrop-blur-sm bg-card/90 transition-colors hover:bg-card"
    >
      <div className="flex items-center justify-between gap-4">
        <h3 className="font-medium text-foreground">{question}</h3>
        <ChevronDown
          className={`w-4 h-4 text-muted-foreground shrink-0 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </div>
      {open && (
        <p className="text-sm text-muted-foreground mt-3 leading-relaxed">
          {answer}
        </p>
      )}
    </button>
  );
}

export function PricingContent() {
  return (
    <main className="relative min-h-screen bg-background overflow-hidden">
      <FlickeringGrid className="absolute inset-0 z-0 opacity-40" />
      <div className="relative z-10">
        <NavHeader />
      </div>
      <div className="relative z-10 w-full max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 pb-24 pt-8">
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
            Start free with the CLI. Upgrade when you want hosted previews or scale.
          </p>
        </m.div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
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
                {tier.priceLabel && (
                  <span className="text-sm text-muted-foreground ml-1">
                    {tier.priceLabel}
                  </span>
                )}
              </div>

              <ul className="space-y-3 mb-8 flex-1">
                {tier.features.map((feature) => (
                  <li
                    key={feature.text}
                    className={`flex items-start gap-2.5 text-sm ${"isSectionLabel" in feature && feature.isSectionLabel ? "mb-1" : ""}`}
                  >
                    {"isSectionLabel" in feature && feature.isSectionLabel ? (
                      <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        {feature.text}
                      </span>
                    ) : (
                      <>
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
                      </>
                    )}
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
        {/* Price anchoring */}
        <m.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.6, ease: "easeOut" }}
          className="mt-16 text-center"
        >
          <p className="text-muted-foreground text-sm max-w-2xl mx-auto leading-relaxed border border-border rounded-lg p-6 backdrop-blur-sm bg-card/90">
            Traditional agency redesigns cost{" "}
            <span className="text-foreground font-medium">$5,000&ndash;$15,000</span>{" "}
            and take 2&ndash;6 months. SastaSpace Pro gives you unlimited redesigns for{" "}
            <span className="text-foreground font-medium">$19/month</span>.
          </p>
        </m.div>

        {/* FAQ */}
        <m.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.7, ease: "easeOut" }}
          className="mt-20"
        >
          <h2 className="font-heading text-2xl text-foreground text-center mb-8">
            Frequently asked questions
          </h2>
          <div className="max-w-2xl mx-auto space-y-3">
            {PRICING_FAQS.map((faq) => (
              <FaqItem key={faq.question} question={faq.question} answer={faq.answer} />
            ))}
          </div>
        </m.div>
      </div>
      <Footer />
    </main>
  );
}
