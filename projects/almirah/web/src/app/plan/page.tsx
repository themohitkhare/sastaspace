import { AppFrame } from "@/components/almirah/app-frame";
import { AppBar } from "@/components/almirah/app-bar";
import { TabBar } from "@/components/almirah/tab-bar";
import { ItemCard } from "@/components/almirah/item-card";
import { IconSparkle } from "@/components/almirah/icons";
import { itemById, type Item } from "@/lib/almirah/items";

export default function Plan() {
  const picks: Array<{ items: Item[]; label: string; reason: string }> = [
    {
      items: ["i05", "i09", "i15", "i12"].map((x) => itemById(x)!).filter(Boolean),
      label: "1 · red kanjivaram",
      reason: "Hasn't been out in 5 months. Reads right for reception-formality.",
    },
    {
      items: ["i08", "i10", "i14"].map((x) => itemById(x)!).filter(Boolean),
      label: "2 · rose lehenga",
      reason: "Lighter feel — good for a daytime reception or haldi-adjacent event.",
    },
    {
      items: ["i07", "i09", "i14"].map((x) => itemById(x)!).filter(Boolean),
      label: "3 · sky chiffon",
      reason: 'Only worn once — you mentioned "pastel preferred" in the notes.',
    },
  ];

  return (
    <AppFrame>
      <AppBar title="Plan an occasion" terminal="~/mk · planner" />
      <div className="scroll scroll--pad">
        <div className="card" style={{ padding: 14, marginTop: 8 }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            <input
              className="field"
              style={{ padding: "10px 12px", fontSize: 14 }}
              defaultValue="Karan's reception"
            />
            <input
              className="field field--mono"
              style={{ padding: "10px 12px", fontSize: 13 }}
              defaultValue="2026-05-18"
            />
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
            <span className="tag tag--active">wedding</span>
            <span className="tag">puja</span>
            <span className="tag">office</span>
            <span className="tag">date</span>
            <span className="tag">casual</span>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center" }}>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "var(--brand-muted)",
              }}
            >
              formality
            </span>
            <div className="segment">
              {[1, 2, 3, 4].map((n) => (
                <button key={n} className={n === 3 ? "active" : ""}>
                  {n}
                </button>
              ))}
            </div>
          </div>
          <div className="meta-mono" style={{ marginTop: 10 }}>
            pastel preferred · indoor · 2026-05-18
          </div>
        </div>

        <div style={{ marginTop: 20 }}>
          <div className="eyebrow" style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <IconSparkle size={14} />
            <span>3 outfits from your rack</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {picks.map((p, i) => (
              <div key={i} className="card" style={{ padding: 14 }}>
                <div
                  style={{
                    display: "flex",
                    alignItems: "baseline",
                    justifyContent: "space-between",
                    marginBottom: 10,
                  }}
                >
                  <div style={{ fontSize: 14, fontWeight: 500, letterSpacing: "-0.005em" }}>
                    {p.label}
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 10,
                      color: "var(--brand-muted)",
                    }}
                  >
                    {p.items.length} pieces
                  </div>
                </div>
                <div className="rail" style={{ padding: 0, position: "relative" }}>
                  <div className="rail-rod" style={{ top: 6 }} />
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: `repeat(${p.items.length}, 1fr)`,
                      gap: 8,
                      paddingTop: 12,
                    }}
                  >
                    {p.items.map((it) => (
                      <div key={it.id} style={{ aspectRatio: "3/4" }}>
                        <ItemCard kind={it.kind} tone={it.tone} size="sm" />
                      </div>
                    ))}
                  </div>
                </div>
                <p style={{ margin: "10px 0 0", fontSize: 13, color: "#3a3834", lineHeight: 1.5 }}>
                  {p.reason}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
      <TabBar active="plan" />
    </AppFrame>
  );
}
