import type { ReactNode } from "react";

export function AppFrame({ children }: { children: ReactNode }) {
  return <div className="app">{children}</div>;
}
