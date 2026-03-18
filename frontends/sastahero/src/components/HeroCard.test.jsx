import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import HeroCard from './HeroCard.jsx';
import useHeroStore from '../store/useHeroStore.js';

describe('HeroCard', () => {
  beforeEach(() => {
    useHeroStore.getState().reset();
  });

  it('renders warrior card by default', () => {
    render(<HeroCard />);
    expect(screen.getByTestId('hero-card')).toBeInTheDocument();
    expect(screen.getByText('Warrior')).toBeInTheDocument();
  });

  it('shows all stat names', () => {
    render(<HeroCard />);
    expect(screen.getByText('STR')).toBeInTheDocument();
    expect(screen.getByText('DEX')).toBeInTheDocument();
    expect(screen.getByText('INT')).toBeInTheDocument();
    expect(screen.getByText('WIS')).toBeInTheDocument();
    expect(screen.getByText('VIT')).toBeInTheDocument();
    expect(screen.getByText('LCK')).toBeInTheDocument();
  });

  it('shows total power', () => {
    render(<HeroCard />);
    expect(screen.getByText('TOTAL POWER')).toBeInTheDocument();
  });

  it('updates when class changes', async () => {
    render(<HeroCard />);
    const { act } = await import('@testing-library/react');
    await act(async () => {
      useHeroStore.getState().setClass('MAGE');
    });
    expect(screen.getByText('Mage')).toBeInTheDocument();
  });
});
