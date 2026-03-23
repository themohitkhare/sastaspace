import { Zap, Github, DollarSign, Unlock } from "lucide-react";

const BADGES = [
  { icon: Zap, label: "60 Seconds", sublabel: "Not 60 days" },
  { icon: Github, label: "Open Source", sublabel: "Inspect, fork, contribute" },
  { icon: DollarSign, label: "$0.10 Per Redesign", sublabel: "vs $5,000+ traditional" },
  { icon: Unlock, label: "Zero Lock-in", sublabel: "Your design, forever" },
] as const;

export function TrustBadges() {
  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="flex flex-wrap items-center justify-center gap-8 sm:gap-12">
        {BADGES.map(({ icon: Icon, label, sublabel }) => (
          <div key={label} className="flex flex-col items-center gap-1.5">
            <Icon className="h-5 w-5 text-muted-foreground/60" strokeWidth={1.5} />
            <span className="text-xs font-medium text-foreground tracking-wide">{label}</span>
            <span className="text-[11px] text-muted-foreground">{sublabel}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
