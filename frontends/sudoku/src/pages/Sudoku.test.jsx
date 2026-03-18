import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
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

describe('Sudoku page advanced controls', () => {
  beforeEach(() => {
    vi.spyOn(global, 'setInterval').mockImplementation(() => 0);
    vi.spyOn(global, 'clearInterval').mockImplementation(() => {});
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: true,
        json: async () => ({
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
        }),
      })),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('keeps the start screen minimal by default and reveals difficulty on Advanced', async () => {
    await act(async () => {
      renderSudokuAt('/');
    });

    expect(screen.getByRole('button', { name: /solve with ga/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /advanced/i })).toBeInTheDocument();
    expect(screen.queryByLabelText(/difficulty picker/i)).not.toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /advanced/i }));

    expect(screen.getByLabelText(/difficulty picker/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /easy/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /medium/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /hard/i })).toBeInTheDocument();
  });

  it('sends selected difficulty when starting a match', async () => {
    await act(async () => {
      renderSudokuAt('/');
    });
    const user = userEvent.setup();

    await user.click(screen.getByRole('button', { name: /advanced/i }));
    await user.click(screen.getByRole('button', { name: /^hard$/i }));
    await user.click(screen.getByRole('button', { name: /solve with ga/i }));

    const startCall = global.fetch.mock.calls.find(([url, init]) => {
      const method = init?.method || 'GET';
      return String(url).includes('/api/v1/sudoku/matches') && method === 'POST';
    });

    expect(startCall).toBeTruthy();
    const [, init] = startCall;
    const body = JSON.parse(init.body);
    expect(body.difficulty).toBe('hard');
  });
});

