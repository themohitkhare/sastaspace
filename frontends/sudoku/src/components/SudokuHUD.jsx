/**
 * SudokuHUD — Heads-up display showing GA solver progress.
 */
export default function SudokuHUD({ generation, fitness, status }) {
  const fitnessPercent = (fitness * 100).toFixed(1);
  const statusLabel = status === 'solved' ? 'SOLVED' : status === 'solving' ? 'SOLVING...' : status.replace(/_/g, ' ').toUpperCase();

  return (
    <div className="hud" data-testid="sudoku-hud">
      <div className="hud-stat">
        <div className="label">GENERATION</div>
        <div className="value generation">{generation}</div>
      </div>
      <div className="hud-stat">
        <div className="label">FITNESS</div>
        <div className="value fitness">{fitnessPercent}%</div>
        <div className="fitness-bar">
          <div
            className="fitness-bar-fill"
            style={{ width: `${fitnessPercent}%` }}
          />
        </div>
      </div>
      <div className="hud-stat">
        <div className="label">STATUS</div>
        <div className="value" style={{ fontSize: '0.85rem' }}>
          {statusLabel}
        </div>
      </div>
    </div>
  );
}
