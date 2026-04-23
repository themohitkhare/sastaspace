import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

/**
 * Status chip — the signature shape of the SastaSpace brand.
 * Encodes project *state*, not metrics. See brand/BRAND_GUIDE.md §6.
 */
const chipStyles = cva(
  [
    "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1",
    "font-mono text-[11px] tracking-[0.05em]",
    "before:inline-block before:h-1.5 before:w-1.5 before:rounded-full before:content-['']",
  ],
  {
    variants: {
      value: {
        live: "bg-[var(--brand-ink)] text-[var(--brand-paper)] before:bg-[#8cc67a] dark:bg-[var(--brand-paper)] dark:text-[var(--brand-ink)]",
        wip: "bg-[var(--brand-sasta)] text-[var(--brand-paper)] before:bg-[var(--brand-paper)]",
        paused:
          "bg-transparent text-muted-foreground border border-border before:bg-[var(--brand-dust)]",
        archived:
          "bg-transparent text-muted-foreground border border-dashed border-border before:border before:border-[var(--brand-dust)] before:bg-transparent",
        "open-source":
          "bg-transparent text-foreground border border-foreground before:bg-foreground",
      },
    },
    defaultVariants: { value: "live" },
  },
);

const LABELS: Record<StatusValue, string> = {
  live: "live",
  wip: "wip",
  paused: "paused",
  archived: "archived",
  "open-source": "open source",
};

export type StatusValue = NonNullable<VariantProps<typeof chipStyles>["value"]>;

export function StatusChip({
  value,
  className,
}: {
  value: StatusValue;
  className?: string;
}) {
  return (
    <span
      className={cn(chipStyles({ value }), className)}
      aria-label={`status: ${LABELS[value]}`}
    >
      {LABELS[value]}
    </span>
  );
}
