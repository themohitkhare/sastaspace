'use client';
import { useState, useRef, useCallback, useEffect } from 'react';
import type { Region, Player, LegionId } from '@/types';
import { LEGION_INFO } from '@/lib/legions';
import { MAP_REGIONS, CONTINENTS } from '@/lib/regions';
import RegionDetail from './RegionDetail';

interface Props {
  regions: Region[];
  player: Player;
  onEnter: (r: Region) => void;
  onOpenBoard: () => void;
  onSwapLegion: () => void;
}

const MAP_W = 1200;
const MAP_H = 800;
const SVG_W = 760;
const SVG_H = 480;

function project3D(
  x: number,
  y: number,
  tilt: number,
  yaw: number,
  scale: number,
  cx: number,
  cy: number,
  mapW: number,
  mapH: number
): [number, number] {
  const nx = (x / mapW) * 2 - 1;
  const ny = (y / mapH) * 2 - 1;
  const cosY = Math.cos(yaw);
  const sinY = Math.sin(yaw);
  const rx = nx * cosY - ny * sinY;
  const ry = nx * sinY + ny * cosY;
  const cosT = Math.cos(tilt);
  const pz = ry * Math.sin(tilt);
  const py = ry * cosT;
  const screenX = cx + rx * scale;
  const screenY = cy + py * scale - pz * scale * 0.3;
  return [screenX, screenY];
}

function polyPoints(
  pts: [number, number][],
  tilt: number,
  yaw: number,
  scale: number,
  cx: number,
  cy: number
): string {
  return pts
    .map(([x, y]) => project3D(x, y, tilt, yaw, scale, cx, cy, MAP_W, MAP_H).join(','))
    .join(' ');
}

export default function MapWarMap({ regions, player, onEnter, onOpenBoard, onSwapLegion }: Props) {
  const [tilt, setTilt] = useState(0.55);
  const [yaw, setYaw] = useState(0);
  const [scale, setScale] = useState(380);
  const [cx, setCx] = useState(SVG_W / 2);
  const [cy, setCy] = useState(SVG_H / 2 + 20);
  const [selected, setSelected] = useState<Region | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);

  const dragRef = useRef<{ startX: number; startY: number; startYaw: number; startTilt: number } | null>(null);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    dragRef.current = { startX: e.clientX, startY: e.clientY, startYaw: yaw, startTilt: tilt };
  }, [yaw, tilt]);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      setYaw(dragRef.current.startYaw + dx * 0.003);
      setTilt(Math.max(0.1, Math.min(1.2, dragRef.current.startTilt - dy * 0.003)));
    };
    const onUp = () => { dragRef.current = null; };
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    };
  }, []);

  const myLegion = LEGION_INFO[player.legion];

  const liberated = regions.filter(r => r.controlling_legion !== -1);
  const contested = regions.filter(r => r.controlling_legion === -1 && r.enemy_hp < r.enemy_max_hp);
  const pristine = regions.filter(r => r.controlling_legion === -1 && r.enemy_hp === r.enemy_max_hp);

  const tierCount = (tier: 1 | 2 | 3) => regions.filter(r => r.controlling_legion !== -1 && r.tier === tier).length;

  return (
    <div className="page" style={{ background: 'var(--brand-paper)' }}>
      <header className="topbar">
        <span className="ss-mono" style={{ fontWeight: 600 }}>typewars.sastaspace.com</span>
        <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>season 1 · day 12 / 30</span>
        <span style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          <button
            className="player-pill swap-pill"
            onClick={onSwapLegion}
            style={{ cursor: 'pointer' }}
          >
            <span className="player-dot" style={{ background: myLegion.color }} />
            <span className="ss-label">{player.username}</span>
            <span className="ss-small ss-mono" style={{ color: 'var(--brand-muted)' }}>· {myLegion.short}</span>
          </button>
          <button className="link-btn" onClick={onOpenBoard}>leaderboard</button>
        </span>
      </header>

      <div className="map-layout">
        {/* Left: map stage */}
        <div className="map-stage">
          <div>
            <p className="ss-eyebrow" style={{ color: 'var(--brand-muted)', marginBottom: 8 }}>war map · season 1</p>
            <h1 className="ss-h2" style={{ margin: 0 }}>The Contested Worlds</h1>
          </div>

          <div className="map-frame" style={{ width: '100%' }}>
            <div className="map-frame-bg" />
            <svg
              className="map-svg"
              width={SVG_W}
              height={SVG_H}
              viewBox={`0 0 ${SVG_W} ${SVG_H}`}
              onMouseDown={onMouseDown}
            >
              {/* Ocean plane */}
              <rect x={0} y={0} width={SVG_W} height={SVG_H} fill="var(--brand-paper-sunken)" />

              {/* Continent shadows */}
              {CONTINENTS.map((cont, ci) => (
                <polygon
                  key={`shadow-${ci}`}
                  points={polyPoints(cont as [number,number][], tilt, yaw, scale, cx + 3, cy + 4)}
                  fill="rgba(168,161,150,0.18)"
                />
              ))}

              {/* Continent fills */}
              {CONTINENTS.map((cont, ci) => (
                <polygon
                  key={`cont-${ci}`}
                  points={polyPoints(cont as [number,number][], tilt, yaw, scale, cx, cy)}
                  fill="var(--brand-paper-lifted)"
                  stroke="var(--brand-dust-40)"
                  strokeWidth={1}
                />
              ))}

              {/* Region pins */}
              {MAP_REGIONS.map((pos, i) => {
                const r = regions[i];
                if (!r) return null;
                const [px, py] = project3D(pos.x, pos.y, tilt, yaw, scale, cx, cy, MAP_W, MAP_H);
                const isSelected = selected?.id === i;
                const isHov = hovered === i;
                const isLiberated = r.controlling_legion !== -1;
                const legColor = isLiberated ? LEGION_INFO[r.controlling_legion as LegionId].color : 'var(--brand-sasta)';
                const r2 = r.tier === 1 ? 5 : r.tier === 2 ? 7 : 9;

                return (
                  <g key={i} style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHovered(i)}
                    onMouseLeave={() => setHovered(null)}
                    onClick={() => setSelected(selected?.id === i ? null : r)}
                  >
                    {(isSelected || isHov) && (
                      <circle cx={px} cy={py} r={r2 + 6} fill={legColor} opacity={0.2} />
                    )}
                    <circle
                      cx={px} cy={py} r={r2}
                      fill={isLiberated ? legColor : 'var(--brand-paper)'}
                      stroke={legColor}
                      strokeWidth={isSelected ? 2.5 : 1.5}
                    />
                    {isHov && (
                      <text
                        x={px} y={py - r2 - 6}
                        textAnchor="middle"
                        fontSize={10}
                        fontFamily="var(--font-mono)"
                        fill="var(--brand-ink)"
                        style={{ pointerEvents: 'none', userSelect: 'none' }}
                      >
                        {r.name}
                      </text>
                    )}
                  </g>
                );
              })}
            </svg>

            <div className="map-controls">
              <span className="ss-small ss-mono" style={{ color: 'var(--brand-muted)' }}>drag to rotate</span>
              <button className="link-btn" onClick={() => { setTilt(0.55); setYaw(0); }}>reset view</button>
            </div>
          </div>

          {/* Legend */}
          <div className="globe-legend">
            {([0, 1, 2, 3, 4] as LegionId[]).map(id => {
              const info = LEGION_INFO[id];
              const count = regions.filter(r => r.controlling_legion === id).length;
              return (
                <div key={id} className="leg-item">
                  <span className="leg-pip" style={{ background: info.color }} />
                  <span className="ss-small">{info.name}</span>
                  <span className="ss-small ss-mono" style={{ color: 'var(--brand-muted)' }}>{count}</span>
                </div>
              );
            })}
            <div className="leg-item">
              <span className="leg-pip-tier" />
              <span className="ss-small">T1</span>
            </div>
            <div className="leg-item">
              <span className="leg-pip-tier t2" />
              <span className="ss-small">T2</span>
            </div>
            <div className="leg-item">
              <span className="leg-pip-tier t3" />
              <span className="ss-small">T3</span>
            </div>
          </div>
        </div>

        {/* Right: sidebar */}
        <div className="map-side">
          {/* Stats chips */}
          <div className="globe-stats">
            <div className="hud-stat">
              <span className="hud-label">liberated</span>
              <span className="hud-val">{liberated.length}/25</span>
            </div>
            <div className="hud-stat">
              <span className="hud-label">contested</span>
              <span className="hud-val">{contested.length}</span>
            </div>
            <div className="hud-stat">
              <span className="hud-label">pristine</span>
              <span className="hud-val">{pristine.length}</span>
            </div>
          </div>

          {/* Region detail or prompt */}
          {selected ? (
            <RegionDetail
              r={selected}
              onEnter={r => onEnter(r)}
              onClose={() => setSelected(null)}
            />
          ) : (
            <div className="globe-prompt">
              <p className="ss-eyebrow" style={{ color: 'var(--brand-muted)', marginBottom: 8 }}>select a region</p>
              <p className="ss-body" style={{ color: 'var(--brand-muted)' }}>
                Click any node on the map or select from the list below to see battle status and enter a region.
              </p>
            </div>
          )}

          {/* Quick region list */}
          <div className="region-quick-list">
            <div className="rql-head">
              <span className="ss-label">all regions</span>
              <span className="ss-small ss-mono" style={{ color: 'var(--brand-muted)' }}>
                {tierCount(1)}T1 · {tierCount(2)}T2 · {tierCount(3)}T3
              </span>
            </div>
            {regions.map(r => {
              const isSelected = selected?.id === r.id;
              const isLiberated = r.controlling_legion !== -1;
              const legInfo = isLiberated ? LEGION_INFO[r.controlling_legion as LegionId] : null;
              return (
                <button
                  key={r.id}
                  className={`rql-row${isSelected ? ' sel' : ''}`}
                  onClick={() => setSelected(selected?.id === r.id ? null : r)}
                >
                  <span className="rql-id">{String(r.id + 1).padStart(2, '0')}</span>
                  <span className="rql-name">{r.name}</span>
                  <span className="rql-tier">T{r.tier}</span>
                  <span
                    className={`rql-status${isLiberated ? ' held' : ' enemy'}`}
                    style={isLiberated && legInfo ? { background: legInfo.color } : undefined}
                  >
                    {isLiberated && legInfo ? legInfo.short : 'ENEMY'}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      <footer className="footer-sig">
        <span className="ss-small ss-mono">typewars · season 1 · a sasta lab project</span>
      </footer>
    </div>
  );
}
