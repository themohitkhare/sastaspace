import { Gift, Shield, UserX, Sparkles } from "lucide-react";

const BADGES = [
  { icon: Gift, label: "Free Forever" },
  { icon: Shield, label: "Your IP, Your Design" },
  { icon: UserX, label: "No Signup Required" },
  { icon: Sparkles, label: "Built with Claude AI" },
] as const;

export function TrustBadges() {
  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="flex flex-wrap items-center justify-center gap-8 sm:gap-12">
        {BADGES.map(({ icon: Icon, label }) => (
          <div key={label} className="flex flex-col items-center gap-2">
            <Icon className="h-5 w-5 text-muted-foreground/60" strokeWidth={1.5} />
            <span className="text-xs text-muted-foreground tracking-wide">{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
