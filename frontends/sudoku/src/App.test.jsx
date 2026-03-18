import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from './App.jsx';

describe('App', () => {
  it('renders header with hub link, title, and badge', () => {
    window.history.pushState({}, 'Test page', '/sudoku/');
    render(<App />);
    
    expect(
      screen.getByRole('link', { name: /sastaspace/i }),
    ).toHaveAttribute('href', '/');

    // App label + badge still present
    expect(screen.getByText('Sudoku')).toBeInTheDocument();
    expect(screen.getByText('GA Solver')).toBeInTheDocument();
  });
});
