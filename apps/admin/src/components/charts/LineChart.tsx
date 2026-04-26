'use client';

import { useState, useEffect, useRef } from 'react';

type LineChartProps = {
  data: number[];
  color?: string;
  height?: number;
  yMax?: number;
  yLabel?: string;
  fill?: boolean;
};

export default function LineChart({ data, color = 'var(--brand-ink)', height = 180, yMax, yLabel, fill = true }: LineChartProps) {
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
  const max = yMax ?? Math.max(...data) * 1.1;
  const step = chartW / (data.length - 1);
  const pts = data.map((v, i) => [padL + i * step, padT + chartH - (v / max) * chartH]);
  const d = pts.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(' ');
  const area = `${d} L ${padL + chartW} ${padT + chartH} L ${padL} ${padT + chartH} Z`;
  const yTicks = [0, 0.25, 0.5, 0.75, 1].map(p => max * p);

  return (
    <div ref={ref} style={{ width: '100%' }}>
      <svg width={w} height={height} style={{ display: 'block' }}>
        {yTicks.map((t, i) => {
          const y = padT + chartH - (t / max) * chartH;
          return (
            <g key={i}>
              <line x1={padL} y1={y} x2={padL + chartW} y2={y} stroke="var(--color-border)" strokeWidth="0.5" strokeDasharray={i === 0 ? '0' : '2 3'}/>
              <text x={padL - 6} y={y + 3} fontSize="10" fontFamily="var(--font-mono)" fill="var(--color-fg-muted)" textAnchor="end">{Math.round(t)}{yLabel ?? ''}</text>
            </g>
          );
        })}
        <text x={padL} y={height - 6} fontSize="10" fontFamily="var(--font-mono)" fill="var(--color-fg-muted)">-60m</text>
        <text x={padL + chartW / 2} y={height - 6} fontSize="10" fontFamily="var(--font-mono)" fill="var(--color-fg-muted)" textAnchor="middle">-30m</text>
        <text x={padL + chartW} y={height - 6} fontSize="10" fontFamily="var(--font-mono)" fill="var(--color-fg-muted)" textAnchor="end">now</text>
        {fill && <path d={area} fill={color} opacity="0.1"/>}
        <path d={d} stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </div>
  );
}
