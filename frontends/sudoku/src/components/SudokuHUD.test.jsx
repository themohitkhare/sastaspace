import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import SudokuHUD from '../components/SudokuHUD.jsx';

describe('SudokuHUD', () => {
  it('renders generation and fitness', () => {
    render(<SudokuHUD generation={42} fitness={0.85} status="in_progress" />);
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('85.0%')).toBeInTheDocument();
    expect(screen.getByText('in progress')).toBeInTheDocument();
  });
});
