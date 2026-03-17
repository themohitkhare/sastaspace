import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import App from './App.jsx';

describe('App', () => {
  it('renders without crashing and includes the router basename', () => {
    window.history.pushState({}, 'Test page', '/sudoku/');
    render(<App />);
    
    // Check for the main header to ensure the app wrapper renders
    expect(screen.getByText('SastaSpace Sudoku')).toBeInTheDocument();
    expect(screen.getByText('GA Solver')).toBeInTheDocument();
  });
});
