import type { ReactNode } from "react";

type Props = {
  summary: string;
  children: ReactNode;
  defaultOpen?: boolean;
};

export function Drawer({ summary, children, defaultOpen = false }: Props) {
  return (
    <details open={defaultOpen}>
      <summary>{summary}</summary>
      <div className="body">{children}</div>
    </details>
  );
}
