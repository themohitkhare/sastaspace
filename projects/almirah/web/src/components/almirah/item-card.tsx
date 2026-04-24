import type { ItemKind, ItemTone } from "@/lib/almirah/items";
import { TONE_BG } from "@/lib/almirah/items";
import { ItemShapes } from "./item-shapes";

export type ItemCardSize = "sm" | "md" | "lg";

interface ItemCardProps {
  kind: ItemKind;
  name?: string | null;
  tone?: ItemTone;
  size?: ItemCardSize;
  note?: string;
  faded?: boolean;
  selected?: boolean;
  meta?: string;
}

export function ItemCard({
  kind,
  name,
  tone = "warm",
  size = "md",
  note,
  faded = false,
  selected = false,
  meta,
}: ItemCardProps) {
  const toneBg = TONE_BG[tone];
  const pad = size === "sm" ? "8px" : size === "lg" ? "18px" : "12px";
  const nameFontSize = size === "sm" ? 9 : 10;
  const maxSilhouetteHeight = size === "sm" ? 80 : size === "lg" ? 180 : 130;

  return (
    <div
      style={{
        background: toneBg,
        border: selected ? "1.5px solid var(--brand-sasta)" : "1px solid var(--brand-dust-40)",
        borderRadius: 10,
        padding: pad,
        display: "flex",
        flexDirection: "column",
        alignItems: "stretch",
        gap: size === "sm" ? 6 : 8,
        opacity: faded ? 0.45 : 1,
        position: "relative",
        minHeight: 0,
        height: "100%",
        width: "100%",
      }}
    >
      <div
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#1a1917",
          minHeight: 0,
        }}
      >
        <svg
          viewBox="0 0 100 100"
          width="100%"
          height="100%"
          preserveAspectRatio="xMidYMid meet"
          style={{ maxHeight: maxSilhouetteHeight }}
          aria-hidden="true"
        >
          {ItemShapes[kind]}
        </svg>
      </div>
      {name && (
        <div
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: nameFontSize,
            color: "var(--brand-ink)",
            letterSpacing: "0.03em",
            lineHeight: 1.3,
            textAlign: "left",
          }}
        >
          {name}
          {meta && (
            <div style={{ color: "var(--brand-muted)", marginTop: 1 }}>{meta}</div>
          )}
        </div>
      )}
      {note && (
        <div
          style={{
            position: "absolute",
            top: 6,
            right: 6,
            fontFamily: "var(--font-mono)",
            fontSize: 9,
            background: "var(--brand-ink)",
            color: "var(--brand-paper)",
            padding: "1px 6px",
            borderRadius: 4,
            letterSpacing: "0.04em",
          }}
        >
          {note}
        </div>
      )}
    </div>
  );
}
