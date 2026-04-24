import Link from "next/link";
import { notFound } from "next/navigation";
import { AppFrame } from "@/components/almirah/app-frame";
import { AppBar } from "@/components/almirah/app-bar";
import { ItemCard } from "@/components/almirah/item-card";
import { ItemSilhouette } from "@/components/almirah/item-shapes";
import { IconBack, IconMore, IconWand } from "@/components/almirah/icons";
import {
  ITEMS,
  itemById,
  TONE_BG,
  TONE_SWATCH,
  type Item,
} from "@/lib/almirah/items";

type PairingDeck = { title: string; items: Item[] };

const PAIRINGS: Record<string, PairingDeck[]> = {
  i05: [
    { title: "formal — wedding",   items: ["i09", "i15", "i12"].map((x) => itemById(x)!).filter(Boolean) },
    { title: "understated — puja", items: ["i10", "i14", "i11"].map((x) => itemById(x)!).filter(Boolean) },
  ],
};

function defaultPairings(item: Item): PairingDeck[] {
  // pick 3-6 complementary items from the same rack
  const rackMates = ITEMS.filter((i) => i.rack === item.rack && i.id !== item.id).slice(0, 6);
  const first = rackMates.slice(0, 3);
  const second = rackMates.slice(3, 6);
  return [
    { title: "a natural pairing", items: first },
    ...(second.length >= 2 ? [{ title: "an alternate", items: second }] : []),
  ];
}

export async function generateStaticParams() {
  return ITEMS.map((i) => ({ id: i.id }));
}

export default async function ItemDetail({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const hero = itemById(id);
  if (!hero) notFound();

  const pairings = PAIRINGS[hero.id] ?? defaultPairings(hero);

  return (
    <AppFrame>
      <AppBar
        left={
          <Link href="/" className="iconbtn" aria-label="back">
            <IconBack />
          </Link>
        }
        right={
          <button className="iconbtn" aria-label="more">
            <IconMore />
          </button>
        }
      />
      <div className="scroll" style={{ padding: "4px 20px 96px" }}>
        <div className="stage" style={{ background: TONE_BG[hero.tone] }}>
          <div className="stage-hangerline" />
          <ItemSilhouette kind={hero.kind} size={200} color="#1a1917" />
          <div
            style={{
              position: "absolute",
              bottom: 10,
              left: 14,
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              color: "var(--brand-ink)",
              letterSpacing: "0.04em",
              background: "rgba(245,241,232,0.7)",
              padding: "2px 6px",
              borderRadius: 4,
            }}
          >
            pulled from {hero.rack}
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <h1 style={{ fontSize: 22, fontWeight: 500, letterSpacing: "-0.015em", margin: 0, lineHeight: 1.2 }}>
            {hero.name.charAt(0).toUpperCase() + hero.name.slice(1)}
          </h1>
          <div style={{ marginTop: 6, display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span className="tag">
              <span className="swatch" style={{ background: TONE_SWATCH[hero.tone] }} />
              {hero.tone}
            </span>
            <span className="tag">{hero.kind}</span>
            <span className="tag">₹{hero.price.toLocaleString("en-IN")}</span>
            <span className="tag">last {hero.lastWorn} ago</span>
          </div>
          <div style={{ marginTop: 10 }} className="meta-mono">
            worn {hero.wears} times · last wear {hero.lastWorn} ago
          </div>
        </div>

        <div style={{ marginTop: 26 }}>
          <div className="eyebrow" style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 10 }}>
            <IconWand size={14} />
            <span>complete the look</span>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {pairings.map((p) => (
              <div key={p.title} className="card" style={{ padding: 14 }}>
                <div style={{ fontSize: 13, fontWeight: 500, letterSpacing: "-0.005em", marginBottom: 10 }}>
                  {p.title}
                </div>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: `repeat(${p.items.length}, 1fr)`,
                    gap: 8,
                  }}
                >
                  {p.items.map((it) => (
                    <Link key={it.id} href={`/item/${it.id}`} style={{ aspectRatio: "3/4", textDecoration: "none" }}>
                      <ItemCard kind={it.kind} tone={it.tone} size="sm" />
                    </Link>
                  ))}
                </div>
                <div style={{ display: "flex", gap: 8, marginTop: 10 }}>
                  <button className="btn btn--sm btn--primary" style={{ flex: 1, justifyContent: "center" }}>
                    save as outfit
                  </button>
                  <button className="btn btn--sm btn--ghost" style={{ flex: 1, justifyContent: "center" }}>
                    swap one
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <Link
          href="/search"
          className="btn btn--ghost btn--block"
          style={{ marginTop: 18, color: "var(--brand-muted)" }}
        >
          show similar items in your rack
        </Link>
      </div>
    </AppFrame>
  );
}
