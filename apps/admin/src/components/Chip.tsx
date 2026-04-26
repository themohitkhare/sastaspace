type ChipProps = { status: string; label?: string };

export default function Chip({ status, label }: ChipProps) {
  return (
    <span className={`chip chip--${status}`}>
      <span className="chip__dot"/>
      {label || status}
    </span>
  );
}
