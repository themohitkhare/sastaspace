import Link from "next/link";
import {
  itemsByRack,
  COUNT_IN_ROTATION,
  type Rack as RackType,
} from "@/lib/almirah/items";
import { ItemCard } from "./item-card";

export function Rack({
  title,
  rack,
  big = false,
}: {
  title: string;
  rack: RackType;
  big?: boolean;
}) {
  const items = itemsByRack(rack);
  return (
    <section className="rack">
      <div className="rack-head">
        <h3>{title}</h3>
        <span className="count">
          {items.length} items · {COUNT_IN_ROTATION(items)} in rotation
        </span>
      </div>
      <div className="rail">
        <div className="rail-rod" />
        <div className="rail-scroll">
          {items.map((it) => (
            <Link key={it.id} href={`/item/${it.id}`} className={`rail-item ${big ? "rail-item--lg" : ""}`}>
              <ItemCard
                kind={it.kind}
                name={it.name.split(" ").slice(0, 2).join(" ")}
                tone={it.tone}
                size="sm"
              />
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}
