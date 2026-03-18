import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StatAllocator from './StatAllocator.jsx';
import useHeroStore, { TOTAL_BONUS_POINTS } from '../store/useHeroStore.js';

describe('StatAllocator', () => {
  beforeEach(() => {
    useHeroStore.getState().reset();
  });

  it('renders all stats', () => {
    render(<StatAllocator />);
    expect(screen.getByText('STR')).toBeInTheDocument();
    expect(screen.getByText('LCK')).toBeInTheDocument();
  });

  it('shows full points remaining at start', () => {
    render(<StatAllocator />);
    expect(screen.getByText(`${TOTAL_BONUS_POINTS} / ${TOTAL_BONUS_POINTS} pts left`)).toBeInTheDocument();
  });

  it('decrements remaining points when stat is incremented', () => {
    render(<StatAllocator />);
    const incButtons = screen.getAllByLabelText(/Increase/);
    fireEvent.click(incButtons[0]);
    expect(screen.getByText(`${TOTAL_BONUS_POINTS - 1} / ${TOTAL_BONUS_POINTS} pts left`)).toBeInTheDocument();
  });

  it('can decrement a stat that was incremented', () => {
    render(<StatAllocator />);
    const incButtons = screen.getAllByLabelText(/Increase/);
    fireEvent.click(incButtons[0]);
    const decButtons = screen.getAllByLabelText(/Decrease/);
    fireEvent.click(decButtons[0]);
    expect(screen.getByText(`${TOTAL_BONUS_POINTS} / ${TOTAL_BONUS_POINTS} pts left`)).toBeInTheDocument();
  });

  it('disables increment buttons when no points remain', () => {
    render(<StatAllocator />);
    const incButtons = screen.getAllByLabelText(/Increase/);
    // Spend all 30 points across stats (rotate through them)
    let spent = 0;
    while (spent < TOTAL_BONUS_POINTS) {
      for (let i = 0; i < incButtons.length && spent < TOTAL_BONUS_POINTS; i++) {
        if (!incButtons[i].disabled) {
          fireEvent.click(incButtons[i]);
          spent++;
        }
      }
    }
    expect(screen.getByText(`0 / ${TOTAL_BONUS_POINTS} pts left`)).toBeInTheDocument();
    // No more points — all increment buttons should be disabled
    incButtons.forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });
});
