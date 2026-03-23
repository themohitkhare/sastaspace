const TESTIMONIALS = [
  {
    quote:
      "I pasted my URL expecting a gimmick. What came back looked better than what my agency delivered last quarter.",
    name: "Sarah Chen",
    role: "Head of Marketing",
    company: "Nordvik Analytics",
  },
  {
    quote:
      "We used the AI redesign as a starting point for our rebrand. Saved us weeks of back-and-forth with designers.",
    name: "James Okafor",
    role: "Co-founder",
    company: "Relay Commerce",
  },
  {
    quote:
      "Showed the before/after to our board and got budget approved for a full site overhaul the same day.",
    name: "Priya Sharma",
    role: "VP of Product",
    company: "Mapleleaf SaaS",
  },
];

export function Testimonials() {
  return (
    <div className="w-full max-w-6xl mx-auto">
      <h2 className="font-heading text-2xl sm:text-3xl text-foreground text-center mb-12">
        What people are saying
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {TESTIMONIALS.map((t) => (
          <div
            key={t.name}
            className="rounded-xl border border-border/50 bg-background p-6 flex flex-col"
          >
            <span className="text-3xl text-muted-foreground/30 font-serif leading-none select-none">
              &ldquo;
            </span>
            <p className="text-sm text-muted-foreground mt-2 flex-1 leading-relaxed">
              {t.quote}
            </p>
            <div className="mt-6 pt-4 border-t border-border/30">
              <p className="text-sm font-medium text-foreground">{t.name}</p>
              <p className="text-xs text-muted-foreground">
                {t.role}, {t.company}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
