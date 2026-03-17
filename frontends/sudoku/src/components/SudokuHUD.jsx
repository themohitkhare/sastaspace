/**
 * SudokuHUD — Heads-up display showing generation count, fitness, and status.
 *
 * Props:
 *   generation: number
 *   fitness: number (0–1)
 *   status: string
 */
export default function SudokuHUD({ generation, fitness, status }) {
  const fitnessPercent = (fitness * 100).toFixed(1);

  return (
    <div className="hud" data-testid="sudoku-hud">
      <div className="hud-stat">
        <div className="label">Generation</div>
        <div className="value generation">{generation}</div>
      </div>
      <div className="hud-stat">
        <div className="label">AI Fitness</div>
        <div className="value fitness">{fitnessPercent}%</div>
        <div className="fitness-bar">
          <div
            className="fitness-bar-fill"
            style={{ width: `${fitnessPercent}%` }}
          />
        </div>
      </div>
      <div className="hud-stat">
        <div className="label">Status</div>
        <div className="value" style={{ fontSize: '0.85rem', textTransform: 'capitalize' }}>
          {status.replace(/_/g, ' ')}
        </div>
      </div>
    </div>
  );
}
