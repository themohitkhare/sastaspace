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

describe('Sudoku solver page', () => {
  beforeEach(() => {
    vi.spyOn(global, 'setInterval').mockImplementation((fn) => {
      if (typeof fn === 'function') fn();
      return 1;
    });
    vi.spyOn(global, 'clearInterval').mockImplementation(() => {});

    vi.stubGlobal(
      'fetch',
      vi.fn(async (url, init = {}) => {
        const method = (init.method || 'GET').toUpperCase();
        const path = String(url);

        if (path.endsWith('/api/v1/sudoku/extract-board') && method === 'POST') {
          return {
            ok: true,
            json: async () => ({
              board: Array.from({ length: 81 }, (_, i) => (i % 2 === 0 ? 1 : 0)),
              confidences: Array.from({ length: 81 }, (_, i) => (i % 3 === 0 ? 0.4 : 0.9)),
            }),
          };
        }

        if (path.endsWith('/api/v1/sudoku/matches') && method === 'POST') {
          return { ok: true, json: async () => makeMatchResponse() };
        }

        if (path.includes('/api/v1/sudoku/matches/') && method === 'GET') {
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

        return { ok: true, json: async () => ({}) };
      }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it('shows the solver start screen with puzzle input', async () => {
    await act(async () => {
      renderSudokuAt('/');
    });

    expect(screen.getByText(/SUDOKU SOLVER/i)).toBeInTheDocument();
    expect(screen.getByText(/PASTE SCREENSHOT/i)).toBeInTheDocument();
  });

  it('starts solving and shows GA board with HUD', async () => {
    await act(async () => {
      renderSudokuAt('/');
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /GENERATE & SOLVE/i }));

    expect(await screen.findByTestId('sudoku-hud')).toBeInTheDocument();
    expect(screen.getByTestId('ai-board')).toBeInTheDocument();
  });

  it('updates HUD stats after GA tick polling', async () => {
    await act(async () => {
      renderSudokuAt('/');
    });

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /GENERATE & SOLVE/i }));

    await screen.findByTestId('sudoku-hud');
    expect(await screen.findByText('5')).toBeInTheDocument();
    expect(screen.getByText('50.0%')).toBeInTheDocument();
  });

  it('supports OCR upload and review flow', async () => {
    await act(async () => {
      renderSudokuAt('/');
    });

    const file = new File(['dummy'], 'board.png', { type: 'image/png' });
    const nativeFileInput = document.querySelector('input[type="file"]');
    expect(nativeFileInput).toBeTruthy();

    await act(async () => {
      await fireEvent.change(nativeFileInput, { target: { files: [file] } });
    });

    expect(await screen.findByText(/ocr detected/i)).toBeInTheDocument();

    const clearUncertainBtn = screen.getByRole('button', { name: /CLEAR UNCERTAIN/i });
    const acceptOcrBtn = screen.getByRole('button', { name: /ACCEPT OCR/i });
    expect(clearUncertainBtn).not.toBeDisabled();

    const user = userEvent.setup();
    await user.click(acceptOcrBtn);
    expect(screen.queryByText(/ocr detected/i)).not.toBeInTheDocument();

    // After OCR, solve button should be visible
    expect(screen.getByRole('button', { name: /SOLVE WITH GA/i })).toBeInTheDocument();
  });
});
