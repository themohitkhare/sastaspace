import type { ReactElement } from "react";
import type { ItemKind } from "@/lib/almirah/items";

const ItemShapes: Record<ItemKind, ReactElement> = {
  kurta: (
    <g stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M50 8 V14" />
      <path d="M35 18 Q50 12 65 18" />
      <path d="M35 18 L22 28 L28 36 L36 30 V86 H64 V30 L72 36 L78 28 L65 18" />
      <path d="M50 18 V86" />
    </g>
  ),
  saree: (
    <g stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M50 8 V14" />
      <path d="M32 20 Q50 14 68 20" />
      <path d="M32 20 L28 90 H72 L68 20" />
      <path d="M56 22 Q72 34 66 62 Q60 80 58 90" strokeDasharray="2 3" />
      <path d="M34 38 H66 M34 58 H66 M34 78 H66" strokeDasharray="1 4" />
    </g>
  ),
  blouse: (
    <g stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M50 8 V14" />
      <path d="M36 18 Q50 12 64 18" />
      <path d="M36 18 L26 30 L32 38 L38 32 V58 H62 V32 L68 38 L74 30 L64 18" />
    </g>
  ),
  dupatta: (
    <g stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M50 8 V14" />
      <path d="M30 18 Q50 14 70 18" />
      <path d="M30 18 Q24 60 32 90 H68 Q76 60 70 18" />
      <path d="M34 82 l2 6 M42 86 l2 6 M50 84 l2 8 M58 86 l2 6 M66 82 l2 6" />
    </g>
  ),
  sherwani: (
    <g stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M50 8 V14" />
      <path d="M35 18 Q50 12 65 18" />
      <path d="M35 18 L24 30 V86 H76 V30 L65 18" />
      <path d="M50 18 V86" />
      <path d="M48 30 L52 30 M48 42 L52 42 M48 54 L52 54 M48 66 L52 66" />
    </g>
  ),
  shirt: (
    <g stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M50 8 V14" />
      <path d="M36 18 Q50 12 64 18" />
      <path d="M36 18 L24 28 L30 36 L38 30 V72 H62 V30 L70 36 L76 28 L64 18" />
      <path d="M44 18 L50 26 L56 18" />
    </g>
  ),
  jeans: (
    <g stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M50 8 V14" />
      <path d="M36 18 H64" />
      <path d="M36 18 L32 90 H46 L50 40 L54 90 H68 L64 18" />
      <path d="M36 28 H64" />
    </g>
  ),
  lehenga: (
    <g stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M50 8 V14" />
      <path d="M38 18 Q50 14 62 18" />
      <path d="M38 18 L36 34 H64 L62 18" />
      <path d="M36 34 L22 90 H78 L64 34" />
      <path d="M30 60 H70 M26 76 H74" />
    </g>
  ),
  juttis: (
    <g stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20 70 Q28 54 44 56 L44 68 L18 72 Z" />
      <path d="M54 68 L54 56 Q70 54 80 70 L80 72 L54 68 Z" />
      <path d="M32 60 l0 4 M64 60 l0 4" />
    </g>
  ),
  jacket: (
    <g stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d="M50 8 V14" />
      <path d="M34 18 Q50 12 66 18" />
      <path d="M34 18 L22 30 L30 42 L38 34 V78 H62 V34 L70 42 L78 30 L66 18" />
      <path d="M42 18 L50 32 L58 18" />
      <path d="M50 32 V78" />
    </g>
  ),
};

export function ItemSilhouette({
  kind,
  size = 80,
  color = "currentColor",
}: {
  kind: ItemKind;
  size?: number;
  color?: string;
}) {
  return (
    <svg viewBox="0 0 100 100" width={size} height={size} style={{ color }} aria-hidden="true">
      {ItemShapes[kind]}
    </svg>
  );
}

export { ItemShapes };
