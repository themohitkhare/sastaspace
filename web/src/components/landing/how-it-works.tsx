"use client";

import React from "react";
import { m } from "motion/react";

const steps = [
  {
    number: "1",
    label: "Enter your URL",
    description: "Paste any website address and let our AI take a look.",
  },
  {
    number: "2",
    label: "AI redesigns it",
    description: "Our AI analyzes your site and reimagines it from scratch.",
  },
  {
    number: "3",
    label: "See the result",
    description: "Your redesigned site, ready to preview in seconds.",
  },
];

export function HowItWorks() {
  return (
    <section className="w-full max-w-6xl mx-auto px-6 sm:px-8 lg:px-12 py-20">
      <h2 className="font-heading text-[clamp(1.75rem,4vw,2.5rem)] leading-[1.1] text-foreground mb-16">
        How it works
      </h2>
      <div>
        {steps.map((step, i) => (
          <m.div
            key={step.number}
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.4, delay: i * 0.1 }}
            className="flex gap-8 sm:gap-12 py-10 border-t border-border"
          >
            <span className="font-heading text-[3rem] sm:text-[4rem] leading-none text-accent/40 shrink-0">
              {step.number}
            </span>
            <div className="pt-2">
              <h3 className="text-xl sm:text-2xl font-medium text-foreground mb-2">
                {step.label}
              </h3>
              <p className="text-base text-muted-foreground max-w-md">
                {step.description}
              </p>
            </div>
          </m.div>
        ))}
      </div>
    </section>
  );
}
