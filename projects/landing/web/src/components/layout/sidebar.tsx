"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export type SidebarItem = {
  href: string;
  label: string;
  icon?: LucideIcon;
};

export function Sidebar({ items, title }: { items: SidebarItem[]; title?: string }) {
  const pathname = usePathname();
  return (
    <aside className="hidden w-60 shrink-0 border-r lg:block">
      <div className="flex h-full flex-col gap-1 p-4">
        {title ? (
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {title}
          </p>
        ) : null}
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname?.startsWith(`${href}/`);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
              )}
            >
              {Icon ? <Icon className="h-4 w-4" /> : null}
              <span>{label}</span>
            </Link>
          );
        })}
      </div>
    </aside>
  );
}
