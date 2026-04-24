import Link from "next/link";
import type { ReactNode } from "react";
import { BrandMark } from "./brand-mark";

interface AppBarProps {
  title?: string;
  left?: ReactNode;
  right?: ReactNode;
  terminal?: string;
}

export function AppBar({ title, left, right, terminal }: AppBarProps) {
  return (
    <>
      <div className="appbar">
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {left ?? (
            <Link href="/" className="brand" style={{ textDecoration: "none", color: "inherit" }}>
              <BrandMark size={22} />
              <span>
                almirah<span className="brand-dot" />
              </span>
            </Link>
          )}
          {title && (
            <h1
              style={{
                fontSize: 19,
                fontWeight: 500,
                margin: 0,
                letterSpacing: "-0.015em",
              }}
            >
              {title}
            </h1>
          )}
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>{right}</div>
      </div>
      {terminal && <div className="terminal-anchor">{terminal}</div>}
    </>
  );
}
