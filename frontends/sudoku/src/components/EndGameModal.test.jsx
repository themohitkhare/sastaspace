import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import EndGameModal from '../components/EndGameModal.jsx';

describe('EndGameModal', () => {
  it('shows win message', () => {
    render(<EndGameModal status="player_won" onPlayAgain={() => {}} />);
    expect(screen.getByText(/you win/i)).toBeInTheDocument();
  });

  it('shows lose message', () => {
    render(<EndGameModal status="ai_won" onPlayAgain={() => {}} />);
    expect(screen.getByText(/ai wins/i)).toBeInTheDocument();
  });
});
