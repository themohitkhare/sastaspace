const FAQ_ITEMS = [
  {
    question: "What's the difference between Express and Studio?",
    answer:
      "Express uses fast AI for quick previews — perfect for getting a feel for what's possible. Studio uses premium AI for production-quality designs with more detail and polish.",
  },
  {
    question: "Is it really free?",
    answer:
      "Yes, Express redesigns are completely free. No credit card required. Just enter your URL and see the result.",
  },
  {
    question: "Who owns the redesign?",
    answer:
      "You do. The generated design is yours to use however you like.",
  },
  {
    question: "How does it work?",
    answer:
      "We crawl your site, analyze its content and structure, and use AI to generate a modern redesign while preserving your brand and messaging.",
  },
  {
    question: "Can you build the redesign for real?",
    answer:
      "Absolutely! Use the contact form on your result page to discuss a custom build. I'll turn the AI mockup into a fully functional, production-ready website.",
  },
];

export function FaqSection() {
  return (
    <div className="w-full max-w-2xl mx-auto">
      <h2 className="font-heading text-[clamp(1.75rem,4vw,2.5rem)] leading-[1.1] text-foreground text-center mb-10">
        Frequently asked questions
      </h2>
      <div className="space-y-2">
        {FAQ_ITEMS.map((item) => (
          <details
            key={item.question}
            className="group rounded-lg border border-border bg-background"
          >
            <summary className="flex cursor-pointer items-center justify-between px-5 py-4 text-base font-medium text-foreground select-none list-none [&::-webkit-details-marker]:hidden">
              {item.question}
              <span className="ml-4 shrink-0 text-muted-foreground transition-transform duration-200 group-open:rotate-45">
                +
              </span>
            </summary>
            <div className="px-5 pb-4 text-sm leading-relaxed text-muted-foreground">
              {item.answer}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}
