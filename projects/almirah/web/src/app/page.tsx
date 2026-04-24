import Link from "next/link";
import { AppFrame } from "@/components/almirah/app-frame";
import { AppBar } from "@/components/almirah/app-bar";
import { TabBar } from "@/components/almirah/tab-bar";
import { Rack } from "@/components/almirah/rack";
import { ItemCard } from "@/components/almirah/item-card";
import { IconSearch, IconPlus, IconExternal } from "@/components/almirah/icons";
import { ITEMS, GAP_SUGGESTIONS } from "@/lib/almirah/items";

export default function RackHome() {
  return (
    <AppFrame>
      <AppBar
        right={
          <>
            <Link href="/search" className="iconbtn" aria-label="search">
              <IconSearch />
            </Link>
            <Link href="/onboarding" className="iconbtn" aria-label="add items">
              <IconPlus />
            </Link>
          </>
        }
        terminal={`~/mk · ${ITEMS.length} items · 3 racks`}
      />
      <div className="scroll" style={{ padding: 0 }}>
        <Rack title="Ethnic" rack="ethnic" big />
        <Rack title="Office" rack="office" />
        <Rack title="Weekend" rack="weekend" />

        <section className="rack" style={{ borderBottom: "none" }}>
          <div className="rack-head">
            <h3>Rack&apos;s missing —</h3>
            <Link href="/discover" className="count" style={{ color: "var(--brand-sasta-text)", textDecoration: "none" }}>
              shop the gap →
            </Link>
          </div>
          <div
            style={{
              padding: "4px 20px 4px",
              display: "flex",
              gap: 10,
              overflowX: "auto",
              scrollbarWidth: "none",
            }}
          >
            {GAP_SUGGESTIONS.map((g) => (
              <div key={g.id} className="gap-card">
                <div style={{ aspectRatio: "3/4" }}>
                  <ItemCard kind={g.kind} tone={g.tone} size="md" />
                </div>
                <div style={{ fontSize: 12, fontWeight: 500, lineHeight: 1.3, letterSpacing: "-0.005em" }}>
                  {g.name}
                </div>
                <div style={{ fontSize: 11, color: "var(--brand-muted)", lineHeight: 1.4 }}>{g.reason}</div>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 2 }}>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, color: "var(--brand-ink)" }}>
                    ₹{g.price}
                  </span>
                  <a
                    href={g.url}
                    target="_blank"
                    rel="noreferrer nofollow sponsored"
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                      letterSpacing: "0.04em",
                      color: "var(--brand-sasta-text)",
                      borderBottom: "1px solid currentColor",
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 4,
                      textDecoration: "none",
                    }}
                  >
                    {g.source} <IconExternal size={12} />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
      <TabBar active="rack" />
    </AppFrame>
  );
}
