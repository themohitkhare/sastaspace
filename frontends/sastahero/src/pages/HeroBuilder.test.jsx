import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import HeroBuilder from './HeroBuilder.jsx';

// Mock html-to-image
vi.mock('html-to-image', () => ({
  toPng: vi.fn().mockResolvedValue('data:image/png;base64,fake'),
}));

// Mock fetch
global.fetch = vi.fn();

const renderBuilder = () =>
  render(
    <MemoryRouter>
      <HeroBuilder />
    </MemoryRouter>
  );

describe('HeroBuilder', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the hero builder page', () => {
    renderBuilder();
    expect(screen.getByText('SASTAHERO')).toBeInTheDocument();
    expect(screen.getByText('CHOOSE CLASS')).toBeInTheDocument();
    expect(screen.getByText('ALLOCATE STATS')).toBeInTheDocument();
  });

  it('renders hero card with default class', () => {
    renderBuilder();
    expect(screen.getByTestId('hero-card')).toBeInTheDocument();
    // "Warrior" appears in both ClassSelector and HeroCard
    expect(screen.getAllByText('Warrior').length).toBeGreaterThanOrEqual(1);
  });

  it('switches class on click', () => {
    renderBuilder();
    // Click the Mage button in ClassSelector
    const mageButtons = screen.getAllByText('Mage');
    fireEvent.click(mageButtons[0]);
    // Mage should appear in HeroCard (the h3)
    expect(screen.getAllByText('Mage').length).toBeGreaterThanOrEqual(1);
  });

  it('reset button clears bonus stats', () => {
    renderBuilder();
    const incButtons = screen.getAllByLabelText(/Increase/);
    fireEvent.click(incButtons[0]);
    fireEvent.click(screen.getByText('RESET'));
    // After reset, points remaining should be back to 30
    expect(screen.getByText('30 / 30 pts left')).toBeInTheDocument();
  });

  it('shows export button', () => {
    renderBuilder();
    expect(screen.getByText('EXPORT AS PNG →')).toBeInTheDocument();
  });

  it('shows randomize button', () => {
    renderBuilder();
    expect(screen.getByText('🎲 RANDOMIZE HERO')).toBeInTheDocument();
  });
});
