import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from './App.jsx';

describe('App', () => {
  it('renders header with hub link, title, and badge', () => {
    window.history.pushState({}, 'Test page', '/sudoku/');
    render(<App />);

    expect(
      screen.getByRole('link', { name: /BACK/i }),
    ).toHaveAttribute('href', '/');

    expect(screen.getByText('SUDOKU')).toBeInTheDocument();
    expect(screen.getByText('GA SOLVER')).toBeInTheDocument();
  });
});
