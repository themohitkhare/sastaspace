import { describe, it, expect } from 'vitest';
import { parsePastedBoard } from '../utils/sudokuOcr.js';

describe('parsePastedBoard', () => {
  it('parses space-separated digits', () => {
    const text = Array(81).fill('1').join(' ');
    const board = parsePastedBoard(text, 9);
    expect(board).toHaveLength(81);
    expect(board[0]).toBe(1);
  });

  it('treats dots as zeros', () => {
    const text = Array(81).fill('.').join(' ');
    const board = parsePastedBoard(text, 9);
    expect(board).toHaveLength(81);
    expect(board.every((v) => v === 0)).toBe(true);
  });

  it('returns null for wrong length', () => {
    const board = parsePastedBoard('1 2 3', 9);
    expect(board).toBeNull();
  });

  it('parses comma-separated', () => {
    const text = Array(16).fill('2').join(',');
    const board = parsePastedBoard(text, 4);
    expect(board).toHaveLength(16);
    expect(board[0]).toBe(2);
  });

  it('parses multiline input', () => {
    const rows = Array(9)
      .fill(null)
      .map(() => '1 2 3 4 5 6 7 8 9');
    const board = parsePastedBoard(rows.join('\n'), 9);
    expect(board).toHaveLength(81);
  });
});
