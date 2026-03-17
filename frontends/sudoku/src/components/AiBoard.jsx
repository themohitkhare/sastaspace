/**
 * AiBoard — Read-only board showing AI's best solution with heatmap overlay.
 *
 * Props:
 *   bestBoard: number[]     — AI's current best board
 *   startingBoard: number[] — clue positions
 *   heatmapData: number[]   — per-cell confidence [0,1]
 *   gridSize: number
 */
export default function AiBoard({ bestBoard, startingBoard, heatmapData, gridSize }) {
  const sizeClass = `size-${gridSize}`;

  return (
    <div className="board-panel" data-testid="ai-board">
      <h3><span className="dot dot-ai" /> AI Board <span className="pulse" /></h3>
      <div className={`sudoku-grid ${sizeClass}`}>
        {bestBoard.map((val, idx) => {
          const isClue = startingBoard[idx] !== 0;
          const heat = heatmapData[idx] || 0;
          const heatColor = `rgba(99, 102, 241, ${(heat * 0.6).toFixed(2)})`;

          return (
            <div key={idx} className={`sudoku-cell ${isClue ? 'clue' : ''}`}>
              {!isClue && heat > 0 && (
                <div className="heatmap-bg" style={{ background: heatColor }} />
              )}
              <span style={{ position: 'relative', zIndex: 1 }}>
                {val || ''}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
