const USE_CASES = [
  {
    heading: "See your site reimagined",
    description:
      "Paste any URL and get a full AI-generated redesign in under 60 seconds. No signup, no credit card.",
  },
  {
    heading: "Pitch clients with proof",
    description:
      "Show prospects a before/after of their own website. Close deals faster with tangible results.",
  },
  {
    heading: "Kickstart your rebrand",
    description:
      "Use the AI output as a design reference or starting point. Export the HTML and iterate from there.",
  },
];

export function Testimonials() {
  return (
    <div className="w-full max-w-6xl mx-auto">
      <h2 className="font-heading text-2xl sm:text-3xl text-foreground text-center mb-4">
        How people use SastaSpace
      </h2>
      <p className="text-muted-foreground text-center mb-12 max-w-lg mx-auto">
        A free redesign preview that speaks for itself.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {USE_CASES.map((uc) => (
          <div
            key={uc.heading}
            className="rounded-xl border border-border/50 bg-background p-6 flex flex-col"
          >
            <h3 className="text-base font-medium text-foreground mb-2">
              {uc.heading}
            </h3>
            <p className="text-sm text-muted-foreground leading-relaxed">
              {uc.description}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
