import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import PlayerBoard from '../components/PlayerBoard.jsx';

describe('PlayerBoard', () => {
  const board = [5, 0, 0, 0, 0, 0, 0, 0, 0, ...Array(72).fill(0)];
  const starting = [...board];

  it('renders clue cells as text', () => {
    render(
      <PlayerBoard
        board={board}
        startingBoard={starting}
        gridSize={9}
        onChange={() => {}}
        disabled={false}
      />,
    );
    // The clue "5" should be rendered as text, not an input
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('renders editable cells as inputs', () => {
    render(
      <PlayerBoard
        board={board}
        startingBoard={starting}
        gridSize={9}
        onChange={() => {}}
        disabled={false}
      />,
    );
    // There should be 80 input fields (81 - 1 clue)
    const inputs = screen.getAllByRole('textbox');
    expect(inputs.length).toBe(80);
  });
});
