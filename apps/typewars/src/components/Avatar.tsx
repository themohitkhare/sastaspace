"use client";
import type { LegionId } from "@/types";
import { LEGION_INFO } from "@/lib/legions";

export interface AvatarProps {
  callsign: string;
  legion: LegionId;
  verified: boolean;
  size?: number;
}

export function Avatar({ callsign, legion, verified, size = 24 }: AvatarProps) {
  const letters = (callsign.match(/[A-Za-z]/g)?.join("") ?? callsign)
    .slice(0, 2)
    .toUpperCase();
  const color = LEGION_INFO[legion].color;
  const fontSize = Math.max(10, Math.round(size * 0.42));
  return (
    <span
      className="avatar"
      style={{
        width: size,
        height: size,
        background: color,
        fontSize,
        position: "relative",
      }}
      aria-label={callsign}
    >
      {letters || "?"}
      {verified && <span className="avatar-pip" />}
    </span>
  );
}
