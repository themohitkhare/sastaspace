/**
 * Parse pasted text as a Sudoku board.
 * Accepts whitespace/comma-separated digits, one row per line (or all flat).
 * Dots and zeros both represent empty cells.
 *
 * @param {string} text  — raw pasted text
 * @param {number} gridSize — expected grid size (e.g. 9)
 * @returns {number[]|null} — flat board array or null if parse failed
 */
export function parsePastedBoard(text, gridSize) {
  const n = gridSize;
  const total = n * n;
  // Normalise: replace dots/dashes/underscores with 0, strip junk
  const normalised = text
    .replace(/[.\-_]/g, '0')
    .replace(/[^0-9\s,]/g, '')
    .trim();

  // Split into tokens
  const tokens = normalised.split(/[\s,]+/).filter(Boolean);

  if (tokens.length !== total) return null;

  const board = tokens.map((t) => {
    const v = parseInt(t, 10);
    return Number.isNaN(v) ? 0 : Math.min(v, gridSize);
  });

  return board;
}
