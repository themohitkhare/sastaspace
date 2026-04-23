export type RiskBand = "low" | "mid" | "high";

type Props = {
  label: string;
  value: string;
  subtext: string;
  band: RiskBand;
};

export function RiskCell({ label, value, subtext, band }: Props) {
  return (
    <div className={`risk-cell risk-${band}`}>
      <div className="k">{label}</div>
      <div className="v">{value}</div>
      <div className="t">{subtext}</div>
    </div>
  );
}
