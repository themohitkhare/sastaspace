/**
 * UnifiedBoard — A single Sudoku board for both input and GA visualization.
 *
 * Props:
 *   board: number[]          — current board state (flat array)
 *   startingBoard: number[]  — clue positions (non-zero = clue)
 *   heatmapData: number[]    — per-cell confidence [0,1] from GA. Empty if not solving.
 *   gridSize: number         — 4, 9, or 16
 *   status: string           — 'idle', 'in_progress', 'solved'
 *   onChange: (idx, val) => void
 */
export default function UnifiedBoard({
  board,
  startingBoard,
  heatmapData = [],
  gridSize,
  status,
  onChange,
}) {
  const sizeClass = `size-${gridSize}`;
  const disabled = status !== 'idle'; // Lock input once the GA starts solving

  const handleInput = (idx, e) => {
    const raw = e.target.value.replace(/\D/g, '');
    const val = raw === '' ? 0 : Math.min(parseInt(raw, 10), gridSize);
    onChange(idx, val);
  };

  return (
    <div className="board-panel" data-testid="unified-board">
      <div className={`sudoku-grid ${sizeClass}`}>
        {board.map((val, idx) => {
          const isClue = startingBoard[idx] !== 0;
          const heat = heatmapData[idx] || 0;
          const heatColor = `rgba(99, 102, 241, ${(heat * 0.6).toFixed(2)})`;

          return (
            <div
              key={idx}
              className={`sudoku-cell ${isClue ? 'clue' : 'editable'}`}
            >
              {/* Heatmap bg for the GA solver */}
              {!isClue && heat > 0 && disabled && (
                <div className="heatmap-bg" style={{ background: heatColor }} />
              )}
              
              {isClue ? (
                <span className="cell-value clue-value" style={{ position: 'relative', zIndex: 1 }}>
                  {val}
                </span>
              ) : disabled ? (
                 <span className="cell-value ai-value" style={{ position: 'relative', zIndex: 1, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {val || ''}
                 </span>
              ) : (
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={gridSize > 9 ? 2 : 1}
                  value={val || ''}
                  onChange={(e) => handleInput(idx, e)}
                  disabled={disabled}
                  aria-label={`Cell ${idx}`}
                  style={{ position: 'relative', zIndex: 1 }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
