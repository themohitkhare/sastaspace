'use client';

import { useState, useEffect, useRef } from 'react';

type AreaChartProps = { tx: number[]; rx: number[]; height?: number };

export default function AreaChart({ tx, rx, height = 180 }: AreaChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [w, setW] = useState(800);

  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => setW(e.contentRect.width));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);

  const padL = 36, padR = 8, padT = 8, padB = 22;
  const chartW = Math.max(50, w - padL - padR);
  const chartH = height - padT - padB;
  const max = Math.max(...tx, ...rx) * 1.2;
  const step = chartW / (tx.length - 1);

  const ptsTx = tx.map((v, i) => [padL + i * step, padT + chartH - (v / max) * chartH]);
  const ptsRx = rx.map((v, i) => [padL + i * step, padT + chartH - (v / max) * chartH]);
  const dTx = ptsTx.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(' ');
  const dRx = ptsRx.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(' ');
  const aTx = `${dTx} L ${padL + chartW} ${padT + chartH} L ${padL} ${padT + chartH} Z`;
  const aRx = `${dRx} L ${padL + chartW} ${padT + chartH} L ${padL} ${padT + chartH} Z`;

  return (
    <div ref={ref} style={{ width: '100%' }}>
      <svg width={w} height={height} style={{ display: 'block' }}>
        {[0, 0.25, 0.5, 0.75, 1].map((p, i) => {
          const y = padT + chartH - p * chartH;
          return <line key={i} x1={padL} y1={y} x2={padL + chartW} y2={y} stroke="var(--color-border)" strokeWidth="0.5" strokeDasharray={p === 0 ? '0' : '2 3'}/>;
        })}
        <text x={padL - 6} y={padT + 4} fontSize="10" fontFamily="var(--font-mono)" fill="var(--color-fg-muted)" textAnchor="end">{max.toFixed(1)} Mbps</text>
        <text x={padL - 6} y={padT + chartH + 3} fontSize="10" fontFamily="var(--font-mono)" fill="var(--color-fg-muted)" textAnchor="end">0</text>
        <path d={aRx} fill="var(--brand-sasta)" opacity="0.15"/>
        <path d={dRx} stroke="var(--brand-sasta)" strokeWidth="1.5" fill="none"/>
        <path d={aTx} fill="var(--brand-ink)" opacity="0.1"/>
        <path d={dTx} stroke="var(--brand-ink)" strokeWidth="1.5" fill="none"/>
        <text x={padL} y={height - 6} fontSize="10" fontFamily="var(--font-mono)" fill="var(--color-fg-muted)">-60m</text>
        <text x={padL + chartW} y={height - 6} fontSize="10" fontFamily="var(--font-mono)" fill="var(--color-fg-muted)" textAnchor="end">now</text>
      </svg>
    </div>
  );
}
