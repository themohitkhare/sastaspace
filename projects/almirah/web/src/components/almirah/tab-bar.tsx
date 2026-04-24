import Link from "next/link";
import { IconRack, IconToday, IconPlan, IconMe } from "./icons";

export type TabId = "rack" | "today" | "plan" | "me";

const TABS: Array<{ id: TabId; label: string; href: string; icon: React.ReactElement }> = [
  { id: "rack", label: "the rack", href: "/", icon: <IconRack /> },
  { id: "today", label: "today", href: "/today", icon: <IconToday /> },
  { id: "plan", label: "plan", href: "/plan", icon: <IconPlan /> },
  { id: "me", label: "me", href: "/me", icon: <IconMe /> },
];

export function TabBar({ active }: { active: TabId }) {
  return (
    <nav className="tabbar" aria-label="primary">
      {TABS.map((t) => (
        <Link
          key={t.id}
          href={t.href}
          className={`tab ${active === t.id ? "active" : ""}`}
          aria-current={active === t.id ? "page" : undefined}
        >
          <span className="ico">{t.icon}</span>
          <span>{t.label}</span>
        </Link>
      ))}
    </nav>
  );
}
