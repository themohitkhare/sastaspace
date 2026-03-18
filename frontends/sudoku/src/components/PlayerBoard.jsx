/**
 * PlayerBoard — Interactive Sudoku grid for player input.
 *
 * Props:
 *   board: number[]          — current player board (flat array)
 *   startingBoard: number[]  — clue positions (non-zero = clue)
 *   gridSize: number         — 4, 9, or 16
 *   onChange: (idx, val) => void
 *   disabled: boolean
 *   uncertainCells?: boolean[] — optional OCR uncertainty highlights (flat array)
 */
export default function PlayerBoard({
  board,
  startingBoard,
  gridSize,
  onChange,
  disabled,
  uncertainCells = [],
}) {
  const sizeClass = `size-${gridSize}`;

  const handleInput = (idx, e) => {
    const raw = e.target.value.replace(/\D/g, '');
    const val = raw === '' ? 0 : Math.min(parseInt(raw, 10), gridSize);
    onChange(idx, val);
  };

  return (
    <div className="board-panel" data-testid="player-board">
      <h3><span className="dot dot-player" /> Your Board</h3>
      <div className={`sudoku-grid ${sizeClass}`}>
        {board.map((val, idx) => {
          const isClue = startingBoard[idx] !== 0;
          const isUncertain = Boolean(uncertainCells[idx]);
          return (
            <div
              key={idx}
              className={`sudoku-cell ${isClue ? 'clue' : 'editable'} ${isUncertain ? 'ocr-uncertain' : ''}`}
            >
              {isClue ? (
                val
              ) : (
                <input
                  type="text"
                  inputMode="numeric"
                  maxLength={gridSize > 9 ? 2 : 1}
                  value={val || ''}
                  onChange={(e) => handleInput(idx, e)}
                  disabled={disabled}
                  aria-label={`Cell ${idx}`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
