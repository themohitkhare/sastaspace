import React from "react";

const steps = [
  {
    number: "1",
    label: "Enter your URL",
    description: "Paste any website address",
  },
  {
    number: "2",
    label: "AI redesigns it",
    description: "Our AI analyzes and reimagines your site",
  },
  {
    number: "3",
    label: "See the result",
    description: "Your redesigned site, ready in seconds",
  },
];

export function HowItWorks() {
  return (
    <section className="bg-muted rounded-xl p-8 sm:p-12 w-full max-w-4xl mx-auto">
      <h2 className="text-2xl font-semibold text-foreground text-center mb-8">
        How it works
      </h2>
      <div className="flex flex-col sm:flex-row items-center sm:items-start justify-center gap-8 sm:gap-0">
        {steps.map((step, index) => (
          <React.Fragment key={step.number}>
            {index > 0 && (
              <>
                {/* Desktop connector */}
                <div className="hidden sm:block flex-shrink-0 w-12 h-0.5 bg-border mt-5" />
                {/* Mobile connector */}
                <div className="sm:hidden w-0.5 h-6 bg-border" />
              </>
            )}
            <div className="flex flex-col items-center text-center flex-1">
              <div className="w-10 h-10 rounded-full border-2 border-primary bg-background flex items-center justify-center">
                <span className="text-sm font-semibold text-primary">
                  {step.number}
                </span>
              </div>
              <span className="text-sm text-foreground mt-2">
                {step.label}
              </span>
              <span className="text-sm text-muted-foreground mt-1">
                {step.description}
              </span>
            </div>
          </React.Fragment>
        ))}
      </div>
    </section>
  );
}
