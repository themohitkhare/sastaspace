import { AppFrame } from "@/components/almirah/app-frame";
import { AppBar } from "@/components/almirah/app-bar";
import { TabBar } from "@/components/almirah/tab-bar";
import { ItemCard } from "@/components/almirah/item-card";
import { IconExternal } from "@/components/almirah/icons";
import { GAP_SUGGESTIONS } from "@/lib/almirah/items";

export default function Discover() {
  return (
    <AppFrame>
      <AppBar title="Discover" terminal="~/mk · style coaching" />
      <div className="scroll scroll--pad">
        <div style={{ marginTop: 6 }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>
            this week · silhouette
          </div>
          <h1 className="screen-title" style={{ fontSize: 26 }}>
            Try oversized kurta over narrow pants.
          </h1>
          <p className="screen-sub" style={{ fontSize: 14, marginTop: 8 }}>
            Your ivory chikankari is 2 sizes cleaner over the black trousers than the churidar. Fresh
            silhouette for summer Fridays.
          </p>

          <div className="card" style={{ padding: 14, marginTop: 14 }}>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <div style={{ aspectRatio: "3/4" }}>
                <ItemCard kind="kurta" name="ivory chikankari" tone="cream" size="md" />
              </div>
              <div style={{ aspectRatio: "3/4" }}>
                <ItemCard kind="jeans" name="black trousers" tone="ink" size="md" />
              </div>
            </div>
            <button
              className="btn btn--ghost btn--sm"
              style={{ marginTop: 10, width: "100%", justifyContent: "center" }}
            >
              save as outfit
            </button>
          </div>
        </div>

        <div style={{ marginTop: 28 }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>
            what your rack is missing
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {GAP_SUGGESTIONS.map((g) => (
              <div key={g.id} className="card" style={{ padding: 12, display: "flex", gap: 12 }}>
                <div style={{ width: 86, aspectRatio: "3/4", flexShrink: 0 }}>
                  <ItemCard kind={g.kind} tone={g.tone} size="sm" />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 500, letterSpacing: "-0.005em" }}>
                    {g.name}
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--brand-muted)",
                      margin: "4px 0 8px",
                      lineHeight: 1.45,
                    }}
                  >
                    {g.reason}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                    }}
                  >
                    <span
                      style={{ fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 500 }}
                    >
                      ₹{g.price}
                    </span>
                    <a
                      href={g.url}
                      target="_blank"
                      rel="noreferrer nofollow sponsored"
                      className="btn btn--sm btn--sasta"
                      style={{ fontSize: 11, padding: "5px 10px" }}
                    >
                      {g.source} <IconExternal size={12} />
                    </a>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <p
            className="meta-mono"
            style={{ marginTop: 12, fontSize: 11, lineHeight: 1.6 }}
          >
            external links · almirah earns a small affiliate fee when you buy
          </p>
        </div>
      </div>
      <TabBar active="plan" />
    </AppFrame>
  );
}
