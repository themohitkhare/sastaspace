import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import Sudoku from './Sudoku.jsx';

function renderSudokuAt(pathname = '/') {
  return render(
    <MemoryRouter initialEntries={[pathname]}>
      <Routes>
        <Route path="/" element={<Sudoku />} />
        <Route path="/:matchId" element={<Sudoku />} />
      </Routes>
    </MemoryRouter>,
  );
}

const makeMatchResponse = () => ({
  match_id: 'm1',
  starting_board: new Array(81).fill(0),
  grid_size: 9,
  status: 'in_progress',
  ai: {
    generation_count: 0,
    fitness_score: 0,
    heatmap_data: new Array(81).fill(0),
    best_board: new Array(81).fill(0),
  },
});

describe('Sudoku page end‑to‑end flow', () => {
  beforeEach(() => {
    vi.spyOn(global, 'setInterval').mockImplementation((fn) => {
      // Call immediately to simulate one AI tick, then no-op.
      if (typeof fn === 'function') fn();
      return 1;
    });
    vi.spyOn(global, 'clearInterval').mockImplementation(() => {});

    vi.stubGlobal(
      'fetch',
      vi.fn(async (url, init = {}) => {
        const method = (init.method || 'GET').toUpperCase();
        const path = String(url);

        // OCR extract board
        if (path.endsWith('/api/v1/sudoku/extract-board') && method === 'POST') {
          return {
            ok: true,
            json: async () => ({
              board: Array.from({ length: 81 }, (_, i) => (i % 2 === 0 ? 1 : 0)),
              confidences: Array.from({ length: 81 }, (_, i) => (i % 3 === 0 ? 0.4 : 0.9)),
            }),
          };
        }

        // Start match
        if (path.endsWith('/api/v1/sudoku/matches') && method === 'POST') {
          return {
            ok: true,
            json: async () => makeMatchResponse(),
          };
        }

        // Poll full AI state (GET match)
        if (path.includes('/api/v1/sudoku/matches/') && method === 'GET' && !path.endsWith('/ai-tick')) {
          return {
            ok: true,
            json: async () => ({
              ...makeMatchResponse(),
              ai: {
                generation_count: 5,
                fitness_score: 0.5,
                heatmap_data: new Array(81).fill(0.5),
                best_board: new Array(81).fill(1),
              },
            }),
          };
        }

        // Trigger AI tick
        if (path.endsWith('/ai-tick') && method === 'POST') {
          return {
            ok: true,
            json: async () => ({
              generation_count: 5,
              fitness_score: 0.5,
              status: 'in_progress',
            }),
          };
        }

        // Persist player board
        if (path.includes('/api/v1/sudoku/matches/') && path.endsWith('/board') && method === 'PUT') {
          return {
            ok: true,
            json: async () => ({}),
          };
        }

        // Claim victory
        if (path.endsWith('/claim-victory') && method === 'POST') {
          return {
            ok: true,
            json: async () => ({ valid: true }),
          };
        }

        return {
          ok: true,
          json: async () => ({}),
        };
      }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('starts a match and shows player + AI boards with HUD', async () => {
    await act(async () => {
      renderSudokuAt('/');
    });

    expect(screen.getByText(/sudoku vs\. genetic algorithm/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /start race/i })).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /start race/i }));

    expect(await screen.findByTestId('sudoku-hud')).toBeInTheDocument();
    expect(screen.getByTestId('player-board')).toBeInTheDocument();
    expect(screen.getByTestId('ai-board')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /claim victory/i })).toBeInTheDocument();
  });

  it('updates HUD stats after AI tick polling', async () => {
    await act(async () => {
      renderSudokuAt('/');
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /start race/i }));

    await screen.findByTestId('sudoku-hud');

    expect(await screen.findByText('5')).toBeInTheDocument();
    expect(screen.getByText('50.0%')).toBeInTheDocument();
  });

  it('lets the player claim victory and play again', async () => {
    await act(async () => {
      renderSudokuAt('/');
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /start race/i }));

    await screen.findByTestId('sudoku-hud');

    await user.click(screen.getByRole('button', { name: /claim victory/i }));

    const modal = await screen.findByTestId('end-game-modal');
    expect(modal).toBeInTheDocument();
    expect(screen.getByText(/you win/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /play again/i }));

    expect(await screen.findByRole('button', { name: /start race/i })).toBeInTheDocument();
    expect(screen.queryByTestId('sudoku-hud')).not.toBeInTheDocument();
  });

  it('supports OCR upload and paste review flow on the start screen', async () => {
    await act(async () => {
      renderSudokuAt('/');
    });

    // Mock a small image file for the hidden file input.
    const file = new File(['dummy'], 'board.png', { type: 'image/png' });

    const uploadButton = screen.getByRole('button', { name: /upload image/i });
    expect(uploadButton).toBeInTheDocument();

    // Hidden file input used for uploads.
    const nativeFileInput = document.querySelector('input[type="file"]');
    expect(nativeFileInput).toBeTruthy();

    await act(async () => {
      await fireEvent.change(nativeFileInput, {
        target: { files: [file] },
      });
    });

    // After OCR, review banner should appear.
    expect(
      await screen.findByText(/ocr detected/i),
    ).toBeInTheDocument();

    const clearUncertainBtn = screen.getByRole('button', { name: /clear uncertain/i });
    const acceptOcrBtn = screen.getByRole('button', { name: /accept ocr/i });
    expect(clearUncertainBtn).toBeInTheDocument();
    expect(acceptOcrBtn).toBeInTheDocument();

    // "Clear uncertain" should be enabled because we returned some low-confidence cells.
    expect(clearUncertainBtn).not.toBeDisabled();

    // Accept OCR hides the review UI.
    const user = userEvent.setup();
    await user.click(acceptOcrBtn);
    expect(screen.queryByText(/ocr detected/i)).not.toBeInTheDocument();

    // Now simulate pasting plain text board; this should update the player board.
    const textBoard = '1'.repeat(81);
    await act(async () => {
      fireEvent.paste(window, {
        clipboardData: {
          getData: () => textBoard,
          items: [],
        },
      });
    });

    // After paste, there should still be an editable player board present.
    expect(screen.getByTestId('player-board')).toBeInTheDocument();
  });
});

