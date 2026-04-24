import Link from "next/link";
import { AppFrame } from "@/components/almirah/app-frame";
import { AppBar } from "@/components/almirah/app-bar";
import { TabBar } from "@/components/almirah/tab-bar";
import { ItemCard } from "@/components/almirah/item-card";
import { IconSearch, IconClose, IconSparkle } from "@/components/almirah/icons";
import { ITEMS } from "@/lib/almirah/items";

export default function Search() {
  const query = "something red for a wedding";
  const results = ITEMS.filter((i) => ["red", "rose", "warm"].includes(i.tone)).slice(0, 9);

  return (
    <AppFrame>
      <AppBar
        right={
          <Link href="/" className="iconbtn" aria-label="close">
            <IconClose />
          </Link>
        }
        terminal="~/mk · semantic search"
      />
      <div style={{ padding: "4px 20px 14px" }}>
        <div style={{ position: "relative" }}>
          <span
            style={{
              position: "absolute",
              left: 12,
              top: "50%",
              transform: "translateY(-50%)",
              color: "var(--brand-muted)",
            }}
          >
            <IconSearch />
          </span>
          <input className="field" style={{ paddingLeft: 40 }} defaultValue={query} />
        </div>
      </div>
      <div
        style={{
          padding: "0 20px 10px",
          borderBottom: "1px solid var(--brand-dust-40)",
          display: "flex",
          gap: 8,
          overflowX: "auto",
          scrollbarWidth: "none",
        }}
      >
        <span className="tag tag--sasta" style={{ flexShrink: 0 }}>
          <IconSparkle size={12} /> {results.length} matches
        </span>
        <span className="tag" style={{ flexShrink: 0 }}>
          in ethnic rack
        </span>
        <span className="tag" style={{ flexShrink: 0 }}>
          red · rose · warm
        </span>
      </div>
      <div className="scroll" style={{ padding: "14px 20px 96px" }}>
        <div className="grid-3">
          {results.map((it, i) => (
            <Link
              key={it.id}
              href={`/item/${it.id}`}
              style={{ display: "flex", flexDirection: "column", gap: 4, textDecoration: "none", color: "inherit" }}
            >
              <div style={{ aspectRatio: "3/4" }}>
                <ItemCard kind={it.kind} tone={it.tone} size="sm" />
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  color: "var(--brand-ink)",
                  letterSpacing: "0.03em",
                  lineHeight: 1.3,
                }}
              >
                {it.name}
              </div>
              {i < 3 && (
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: 9,
                    color: "var(--brand-sasta-text)",
                    letterSpacing: "0.04em",
                  }}
                >
                  {Math.round(94 - i * 7)}% match
                </div>
              )}
            </Link>
          ))}
        </div>
      </div>
      <TabBar active="rack" />
    </AppFrame>
  );
}
