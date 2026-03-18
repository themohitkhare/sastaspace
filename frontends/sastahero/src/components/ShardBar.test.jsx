import React from 'react';
import { render, screen } from '@testing-library/react';
import ShardBar from './ShardBar';
import useGameStore from '../store/useGameStore';

describe('ShardBar', () => {
  beforeEach(() => {
    useGameStore.setState({
      shards: { SOUL: 5, SHIELD: 3, VOID: 1, LIGHT: 8, FORCE: 2 },
    });
  });

  it('renders all 5 shard types', () => {
    render(<ShardBar />);
    expect(screen.getByTestId('shard-SOUL')).toBeInTheDocument();
    expect(screen.getByTestId('shard-SHIELD')).toBeInTheDocument();
    expect(screen.getByTestId('shard-VOID')).toBeInTheDocument();
    expect(screen.getByTestId('shard-LIGHT')).toBeInTheDocument();
    expect(screen.getByTestId('shard-FORCE')).toBeInTheDocument();
  });

  it('shows correct shard counts', () => {
    render(<ShardBar />);
    expect(screen.getByTestId('shard-SOUL')).toHaveTextContent('5');
    expect(screen.getByTestId('shard-LIGHT')).toHaveTextContent('8');
  });
});
