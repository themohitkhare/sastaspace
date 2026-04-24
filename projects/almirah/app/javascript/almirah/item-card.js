// ItemCard React island — ported from item-card.tsx.
// Renders a tonal background card with a garment silhouette SVG.
//
// Usage (ERB):
//   <div data-react-component="ItemCard"
//        data-props='{"kind":"kurta","tone":"indigo","name":"indigo block-print kurta","size":"sm"}'>
//   </div>
//
// The mount script at the bottom of application.js finds all
// [data-react-component] elements and mounts them.
import React from "react";
import { SHAPES } from "almirah/item-shapes";

const TONE_BG = {
  cream:  "#f5f1e8",
  indigo: "#dde0ee",
  warm:   "#f5ebe0",
  ink:    "#dcdad6",
  red:    "#f5ddd8",
  olive:  "#e2e8da",
  rose:   "#f5dde8",
  navy:   "#d8dde8",
  sand:   "#ede8da",
  green:  "#dae8dd",
  denim:  "#d8e2ee",
};

function ItemCard({ kind = "shirt", tone = "warm", name, size = "md", note, faded, selected }) {
  const bg = TONE_BG[tone] || "#f5f1e8";
  const pad = size === "sm" ? "8px" : size === "lg" ? "18px" : "12px";
  const nameFontSize = size === "sm" ? 9 : 10;
  const maxSilhouetteHeight = size === "sm" ? 80 : size === "lg" ? 180 : 130;
  const shape = SHAPES[kind] || SHAPES.shirt;

  return React.createElement("div", {
    className: "item-card" + (selected ? " item-card--selected" : "") + (faded ? " item-card--faded" : ""),
    style: {
      background: bg,
      border: selected ? "1.5px solid var(--brand-sasta)" : "1px solid var(--brand-dust-40)",
      padding: pad,
    }
  },
    // Silhouette
    React.createElement("div", { className: "item-card__silhouette" },
      React.createElement("svg", {
        viewBox: "0 0 100 100", width: "100%", height: "100%",
        preserveAspectRatio: "xMidYMid meet",
        style: { maxHeight: maxSilhouetteHeight },
        "aria-hidden": "true"
      }, shape)
    ),
    // Name label
    name ? React.createElement("div", {
      className: "item-card__name" + (size === "sm" ? " item-card__name--sm" : ""),
      style: { fontSize: nameFontSize }
    }, name) : null,
    // Badge / note
    note ? React.createElement("div", { className: "item-card__note" }, note) : null
  );
}

export default ItemCard;
export { ItemCard, TONE_BG };
