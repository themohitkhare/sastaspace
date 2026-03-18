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
});

describe('Sudoku solver page', () => {
  beforeEach(() => {
    vi.spyOn(global, 'setInterval').mockImplementation(() => 1);
    vi.spyOn(global, 'clearInterval').mockImplementation(() => {});

    vi.stubGlobal(
      'fetch',
      vi.fn(async (url, init = {}) => {
        const method = (init.method || 'GET').toUpperCase();
        const path = String(url);

        if (path.endsWith('/extract-board') && method === 'POST') {
          return {
            ok: true,
            json: async () => ({
              board: Array.from({ length: 81 }, (_, i) => (i % 2 === 0 ? 1 : 0)),
              confidences: Array.from({ length: 81 }, (_, i) => (i % 3 === 0 ? 0.4 : 0.9)),
            }),
          };
        }

        if (path.endsWith('/matches') && method === 'POST') {
          return { ok: true, json: async () => makeMatchResponse() };
        }

        if (path.endsWith('/solve') && method === 'POST') {
          return { ok: true, json: async () => ({ match_id: 'm1', status: 'queued' }) };
        }

        if (path.includes('/matches/') && method === 'GET') {
          return {
            ok: true,
            json: async () => ({
              ...makeMatchResponse(),
              status: 'solved',
              ai: {
                generation_count: 5,
                fitness_score: 1.0,
                heatmap_data: new Array(81).fill(0.5),
                best_board: new Array(81).fill(1),
              },
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

  it('shows the solver start screen', async () => {
    await act(async () => { renderSudokuAt('/'); });
    expect(screen.getByText(/SUDOKU SOLVER/i)).toBeInTheDocument();
    expect(screen.getByText(/PASTE SCREENSHOT/i)).toBeInTheDocument();
  });

  it('starts solving and transitions to solve screen', async () => {
    await act(async () => { renderSudokuAt('/'); });
    const user = userEvent.setup();

    await act(async () => {
      await user.click(screen.getByRole('button', { name: /GENERATE RANDOM PUZZLE/i }));
    });

    // After solving starts, the HUD or solved banner should appear
    // (our mock returns status=solved immediately)
    await act(async () => { await new Promise(r => setTimeout(r, 100)); });

    // Verify fetch was called for match creation
    expect(global.fetch).toHaveBeenCalled();
    const calls = global.fetch.mock.calls.map((c) => String(c[0]));
    expect(calls.some((url) => url.includes('/matches'))).toBe(true);
  });

  it('supports OCR upload and review flow', async () => {
    await act(async () => { renderSudokuAt('/'); });
    const file = new File(['dummy'], 'board.png', { type: 'image/png' });
    const nativeFileInput = document.querySelector('input[type="file"]');

    await act(async () => {
      await fireEvent.change(nativeFileInput, { target: { files: [file] } });
    });

    expect(await screen.findByText(/Detected/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /LOOKS GOOD/i })).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /LOOKS GOOD/i }));

    // After accepting, solve button should show
    expect(screen.getByRole('button', { name: /SOLVE/i })).toBeInTheDocument();
  });
});
