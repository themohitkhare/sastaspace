import { AppFrame } from "@/components/almirah/app-frame";
import { AppBar } from "@/components/almirah/app-bar";
import { TabBar } from "@/components/almirah/tab-bar";
import { ItemCard } from "@/components/almirah/item-card";
import { IconMore, IconCheck } from "@/components/almirah/icons";
import { itemById, type Item } from "@/lib/almirah/items";

export default function Today() {
  const today: Item[] = ["i03", "i32", "i14"].map((x) => itemById(x)!).filter(Boolean);
  const alt: Array<{ items: Item[]; note: string }> = [
    {
      items: ["i02", "i24"].map((x) => itemById(x)!).filter(Boolean),
      note: "indigo kurta + black trousers — crisper for the meeting at 3",
    },
    {
      items: ["i20", "i25", "i23"].map((x) => itemById(x)!).filter(Boolean),
      note: "full office: oxford, chinos, blazer — if the client shows up",
    },
  ];

  return (
    <AppFrame>
      <AppBar
        terminal="thu · 23 apr · 28° · sunny"
        right={
          <button className="iconbtn" aria-label="more">
            <IconMore />
          </button>
        }
      />
      <div className="scroll scroll--pad">
        <div style={{ marginTop: 4 }}>
          <div className="eyebrow">today&apos;s pick</div>
          <h1 className="screen-title" style={{ marginTop: 6, fontSize: 28 }}>
            Rust linen, dark denim,
            <br />
            cream juttis.
          </h1>
          <p className="screen-sub" style={{ fontSize: 14, marginTop: 8 }}>
            A notch above office-casual. Haven&apos;t paired these three in ~2 months — fresh rotation.
          </p>
        </div>

        <div className="rail" style={{ marginTop: 18, padding: 0 }}>
          <div className="rail-rod" style={{ top: 10 }} />
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, 1fr)",
              gap: 10,
              paddingTop: 16,
            }}
          >
            {today.map((it) => (
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
        </div>

        <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
          <button className="btn btn--primary" style={{ flex: 1, justifyContent: "center" }}>
            <IconCheck size={16} />
            <span>wearing this</span>
          </button>
          <button className="btn btn--ghost" style={{ flex: 1, justifyContent: "center" }}>
            shuffle
          </button>
        </div>

        <div style={{ marginTop: 30 }}>
          <div className="eyebrow" style={{ marginBottom: 10 }}>
            or try
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {alt.map((set, i) => (
              <div
                key={i}
                className="card"
                style={{ padding: 12, display: "flex", gap: 10, alignItems: "center" }}
              >
                <div style={{ flex: 1, display: "flex", gap: 6 }}>
                  {set.items.map((it) => (
                    <div key={it.id} style={{ flex: 1, aspectRatio: "3/4", maxWidth: 56 }}>
                      <ItemCard kind={it.kind} tone={it.tone} size="sm" />
                    </div>
                  ))}
                </div>
                <div
                  style={{
                    flex: 1.3,
                    fontSize: 12,
                    color: "var(--brand-muted)",
                    lineHeight: 1.4,
                  }}
                >
                  {set.note}
                </div>
                <button className="btn btn--sm btn--ghost">→</button>
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            marginTop: 24,
            padding: 14,
            background: "var(--brand-paper-sunken)",
            borderRadius: 12,
          }}
        >
          <div className="eyebrow" style={{ marginBottom: 6 }}>
            style note
          </div>
          <div style={{ fontSize: 13, lineHeight: 1.55 }}>
            You&apos;ve worn the indigo oxford 3x this week. Your sand linen is cooler and cleaner in 28° heat
            — swap in?
          </div>
        </div>
      </div>
      <TabBar active="today" />
    </AppFrame>
  );
}
