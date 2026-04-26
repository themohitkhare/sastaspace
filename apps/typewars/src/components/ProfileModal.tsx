"use client";
import { useMemo } from "react";
import { useTable } from "spacetimedb/react";
import { tables } from "@sastaspace/typewars-bindings";
import type { LegionId } from "@/types";
import { LEGION_INFO } from "@/lib/legions";
import { Avatar } from "./Avatar";

export interface ProfileModalProps {
  /** Callsign of the player whose profile to display. */
  username: string;
  onClose: () => void;
}

function timeAgo(joinedMs: number): string {
  const sec = Math.max(1, Math.floor((Date.now() - joinedMs) / 1000));
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  return `${day}d ago`;
}

export function ProfileModal({ username, onClose }: ProfileModalProps) {
  const [allPlayers] = useTable(tables.player);
  const [allRegions] = useTable(tables.region);

  const player = useMemo(
    () => allPlayers.find((p) => p.username === username),
    [allPlayers, username],
  );

  if (!player) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div className="modal" onClick={(e) => e.stopPropagation()}>
          <p className="ss-body">Player not found.</p>
          <button className="link-btn" onClick={onClose}>close</button>
        </div>
      </div>
    );
  }

  const legion = player.legion as LegionId;
  const info = LEGION_INFO[legion];
  const verified = player.email != null;
  const joinedMs = Number(player.joinedAt.toMillis());
  const regionsHeld = allRegions.filter((r) => r.controllingLegion === legion).length;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head" style={{ alignItems: "center", gap: 16 }}>
          <Avatar callsign={player.username} legion={legion} verified={verified} size={48} />
          <div style={{ flex: 1 }}>
            <h2 className="ss-h2" style={{ margin: 0 }}>{player.username}</h2>
            <p className="ss-small" style={{ color: "var(--brand-muted)", margin: 0 }}>
              {info.name} · {info.mechanic} · joined {timeAgo(joinedMs)}
              {verified && <span style={{ color: "var(--brand-sasta-text)", marginLeft: 8 }}>✓ verified</span>}
            </p>
          </div>
          <button className="link-btn" onClick={onClose}>close</button>
        </div>
        <div className="personal-grid" style={{ marginTop: 24 }}>
          <div className="hud-stat">
            <span className="hud-label">total dmg</span>
            <span className="hud-val">{Number(player.totalDamage).toLocaleString()}</span>
          </div>
          <div className="hud-stat">
            <span className="hud-label">season dmg</span>
            <span className="hud-val">{Number(player.seasonDamage).toLocaleString()}</span>
          </div>
          <div className="hud-stat">
            <span className="hud-label">best wpm</span>
            <span className="hud-val">{player.bestWpm}</span>
          </div>
          <div className="hud-stat">
            <span className="hud-label">regions held</span>
            <span className="hud-val">{regionsHeld}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
