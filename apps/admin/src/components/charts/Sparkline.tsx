type SparklineProps = {
  data: number[];
  color?: string;
  width?: number;
  height?: number;
  fill?: boolean;
};

export default function Sparkline({ data, color = 'var(--brand-ink)', width = 120, height = 32, fill = false }: SparklineProps) {
  if (!data || !data.length) return null;
  const max = Math.max(...data, 1);
  const step = width / (data.length - 1);
  const pts = data.map((v, i) => [i * step, height - (v / max) * height]);
  const d = pts.map((p, i) => (i === 0 ? `M ${p[0]} ${p[1]}` : `L ${p[0]} ${p[1]}`)).join(' ');
  const area = `${d} L ${width} ${height} L 0 ${height} Z`;
  return (
    <svg className="sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      {fill && <path d={area} fill={color} opacity="0.12"/>}
      <path d={d} stroke={color} strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}
