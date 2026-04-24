import Link from "next/link";
import { AppFrame } from "@/components/almirah/app-frame";
import { AppBar } from "@/components/almirah/app-bar";
import { ItemCard } from "@/components/almirah/item-card";
import { IconClose, IconSparkle } from "@/components/almirah/icons";
import { ITEMS } from "@/lib/almirah/items";

export default function Ingest() {
  const segmented = ITEMS.slice(0, 8);
  const total = 47;
  const processed = 23;
  return (
    <AppFrame>
      <AppBar
        terminal={`~/mk · segmenting ${total} photos → ? items`}
        right={
          <Link href="/" className="iconbtn" aria-label="close">
            <IconClose />
          </Link>
        }
      />
      <div className="scroll scroll--pad">
        <h1 className="screen-title">Unpacking the closet.</h1>
        <p className="screen-sub">
          {processed} of {total} photos processed · 28 items found so far · 4 dupes merged.
        </p>

        <div style={{ marginTop: 16 }}>
          <div className="progress">
            <span style={{ width: `${(processed / total) * 100}%` }} />
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, marginTop: 16, flexWrap: "wrap" }}>
          <div className="statbox">
            <span className="lbl">items</span>
            <span className="val">28</span>
          </div>
          <div className="statbox statbox--sasta">
            <span className="lbl">merged</span>
            <span className="val">4</span>
          </div>
          <div className="statbox statbox--ghost">
            <span className="lbl">queued</span>
            <span className="val">24</span>
          </div>
        </div>

        <div className="eyebrow" style={{ marginTop: 22, marginBottom: 10 }}>
          just extracted
        </div>
        <div className="grid-3">
          {segmented.map((it) => (
            <div key={it.id} style={{ aspectRatio: "3/4" }}>
              <ItemCard
                kind={it.kind}
                name={it.name.split(" ").slice(0, 2).join(" ")}
                tone={it.tone}
                size="sm"
              />
            </div>
          ))}
        </div>

        <div
          style={{
            marginTop: 22,
            padding: 12,
            border: "1px solid var(--brand-dust-40)",
            borderRadius: 12,
            display: "flex",
            gap: 10,
            alignItems: "center",
          }}
        >
          <div
            style={{
              width: 36,
              height: 36,
              borderRadius: 8,
              background: "var(--brand-paper-sunken)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--brand-sasta)",
            }}
          >
            <IconSparkle />
          </div>
          <div style={{ flex: 1, fontSize: 13, lineHeight: 1.45 }}>
            <strong style={{ fontWeight: 500 }}>Merged 2 duplicates.</strong> The indigo block-print kurta
            appears in 3 of your photos — we kept the clearest shot.
          </div>
        </div>

        <Link href="/" className="btn btn--primary btn--block" style={{ marginTop: 22 }}>
          done — take me to the rack →
        </Link>
      </div>
    </AppFrame>
  );
}
