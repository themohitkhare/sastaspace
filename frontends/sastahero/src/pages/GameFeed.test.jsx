import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import GameFeed from './GameFeed';
import useGameStore from '../store/useGameStore';

// Mock fetch
global.fetch = vi.fn(() => Promise.resolve({
  json: () => Promise.resolve({
    stage_number: 1,
    cards: [
      {
        card_id: '1', identity_id: 'genesis', name: 'Genesis',
        types: ['CREATION'], rarity: 'COMMON', shard_yield: 1,
        content_type: 'STORY', text: 'Test', category: null, community_count: 0,
      },
    ],
    shards: { SOUL: 0, SHIELD: 0, VOID: 0, LIGHT: 0, FORCE: 0 },
    stages_completed: 0,
  }),
}));

function renderWithRouter(ui) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('GameFeed', () => {
  beforeEach(() => {
    useGameStore.setState({
      cards: [],
      currentIndex: 0,
      isLoading: false,
      showQuiz: false,
      shards: { SOUL: 0, SHIELD: 0, VOID: 0, LIGHT: 0, FORCE: 0 },
    });
  });

  it('shows loading state initially', () => {
    useGameStore.setState({ isLoading: true, cards: [] });
    renderWithRouter(<GameFeed />);
    expect(screen.getByTestId('game-loading')).toBeInTheDocument();
  });

  it('renders shard bar', () => {
    useGameStore.setState({
      cards: [{
        card_id: '1', identity_id: 'genesis', name: 'Genesis',
        types: ['CREATION'], rarity: 'COMMON', shard_yield: 1,
        content_type: 'STORY', text: 'Test', community_count: 0,
      }],
    });
    renderWithRouter(<GameFeed />);
    expect(screen.getByTestId('shard-bar')).toBeInTheDocument();
  });

  it('renders powerup button when not in quiz', () => {
    useGameStore.setState({
      cards: [{
        card_id: '1', identity_id: 'genesis', name: 'Genesis',
        types: ['CREATION'], rarity: 'COMMON', shard_yield: 1,
        content_type: 'STORY', text: 'Test', community_count: 0,
      }],
    });
    renderWithRouter(<GameFeed />);
    expect(screen.getByTestId('powerup-button')).toBeInTheDocument();
  });
});
