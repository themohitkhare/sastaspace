import { AppFrame } from "@/components/almirah/app-frame";
import { AppBar } from "@/components/almirah/app-bar";
import { TabBar } from "@/components/almirah/tab-bar";
import { ItemCard } from "@/components/almirah/item-card";
import { itemById } from "@/lib/almirah/items";

export default function Me() {
  const mostWorn = ["i31", "i32", "i20"].map((x) => itemById(x)!).filter(Boolean);

  return (
    <AppFrame>
      <AppBar terminal="~/mk · since jan '26" />
      <div className="scroll scroll--pad">
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 4 }}>
          <span className="avatar avatar--lg avatar--ink">M</span>
          <div>
            <div style={{ fontSize: 20, fontWeight: 500, letterSpacing: "-0.015em" }}>Mohit K.</div>
            <div className="meta-mono">mixed · private closet</div>
          </div>
        </div>

        <div style={{ display: "flex", gap: 8, marginTop: 18, flexWrap: "wrap" }}>
          <div className="statbox">
            <span className="lbl">items</span>
            <span className="val">34</span>
          </div>
          <div className="statbox statbox--sasta">
            <span className="lbl">outfits saved</span>
            <span className="val">11</span>
          </div>
          <div className="statbox statbox--ghost">
            <span className="lbl">wears logged</span>
            <span className="val">127</span>
          </div>
        </div>

        <div style={{ marginTop: 26 }}>
          <div className="eyebrow" style={{ marginBottom: 10 }}>
            most-worn this quarter
          </div>
          <div className="grid-3" style={{ gap: 8 }}>
            {mostWorn.map((it) => (
              <div key={it.id} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <div style={{ aspectRatio: "3/4" }}>
                  <ItemCard kind={it.kind} tone={it.tone} size="sm" />
                </div>
                <div className="meta-mono">{it.wears} wears</div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ marginTop: 28 }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>
            preferences
          </div>
          <div className="row">
            <div>
              <div style={{ fontSize: 15, fontWeight: 500 }}>daily pick notification</div>
              <div style={{ fontSize: 13, color: "var(--brand-muted)" }}>
                morning, before you get dressed
              </div>
            </div>
            <span className="toggle on" />
          </div>
          <div className="row">
            <div>
              <div style={{ fontSize: 15, fontWeight: 500 }}>shop-the-gap suggestions</div>
              <div style={{ fontSize: 13, color: "var(--brand-muted)" }}>
                external links in the rack
              </div>
            </div>
            <span className="toggle on" />
          </div>
          <div className="row">
            <div>
              <div style={{ fontSize: 15, fontWeight: 500 }}>trend coaching</div>
              <div style={{ fontSize: 13, color: "var(--brand-muted)" }}>
                weekly silhouette nudges
              </div>
            </div>
            <span className="toggle" />
          </div>
          <div className="row">
            <div>
              <div style={{ fontSize: 15, fontWeight: 500 }}>plan with a friend</div>
              <div style={{ fontSize: 13, color: "var(--brand-muted)" }}>coming in v2</div>
            </div>
            <span className="tag">soon</span>
          </div>
        </div>

        <div
          className="meta-mono"
          style={{ marginTop: 28, lineHeight: 1.7, letterSpacing: "0.06em" }}
        >
          built sasta. shared openly. © mohit khare, 2026.
        </div>
      </div>
      <TabBar active="me" />
    </AppFrame>
  );
}
