/**
 * Tests for GamePage component
 */
import { render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import GamePage from '../../src/pages/GamePage'
import { useGameStore } from '../../src/store/useGameStore'
import { useSastaPolling } from '../../src/hooks/useSastaPolling'

vi.mock('../../src/store/useGameStore')
vi.mock('../../src/hooks/useSastaPolling')
vi.mock('../../src/components/game/BoardView', () => ({
  default: ({ children }) => <div>BoardView{children}</div>,
}))
vi.mock('../../src/components/game/PlayerPanel', () => ({
  default: () => <div>PlayerPanel</div>,
}))
vi.mock('../../src/components/game/ActionPanel', () => ({
  default: () => <div>ActionPanel</div>,
}))
vi.mock('../../src/components/game/DiceDisplay', () => ({
  default: () => <div>DiceDisplay</div>,
}))

describe('GamePage', () => {
  const mockGame = {
    id: 'game-123',
    status: 'ACTIVE',
    turn_phase: 'PRE_ROLL',
    board_size: 6,
    current_turn_player_id: 'player-1',
    starting_cash: 1500,
    go_bonus: 200,
    board: [
      { id: 'tile-1', name: 'Tile 1', x: 0, y: 0, position: 0 },
      { id: 'tile-2', name: 'Tile 2', x: 1, y: 0, position: 1 },
    ],
    players: [
      { id: 'player-1', name: 'Player 1', position: 0, cash: 1500, color: '#FF6B6B' },
      { id: 'player-2', name: 'Player 2', position: 1, cash: 1500, color: '#4ECDC4' },
    ],
  }

  beforeEach(() => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: 'game-123',
        playerId: 'player-1',
        game: mockGame,
        isMyTurn: () => true,
      }
      return selector(state)
    })
    
    // Mock useSastaPolling to return refetch
    useSastaPolling.mockReturnValue({ refetch: vi.fn() })
  })

  it('renders game page with game data', () => {
    render(<GamePage />)
    expect(screen.getByText('SASTADICE')).toBeInTheDocument()
  })

  it('displays game status', () => {
    render(<GamePage />)
    expect(screen.getByText('ACTIVE')).toBeInTheDocument()
  })

  it('displays current turn player', () => {
    render(<GamePage />)
    expect(screen.getByText('PLAYER 1')).toBeInTheDocument()
  })

  it('renders loading state when game is null', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: 'game-123',
        playerId: 'player-1',
        game: null,
        isMyTurn: () => false,
      }
      return selector(state)
    })

    render(<GamePage />)
    expect(screen.getByText('LOADING...')).toBeInTheDocument()
  })

  it('starts polling for game updates', () => {
    render(<GamePage />)
    expect(useSastaPolling).toHaveBeenCalledWith('game-123', 1500)
  })

  it('renders BoardView component', () => {
    render(<GamePage />)
    expect(screen.getByText(/BoardView/)).toBeInTheDocument()
  })

  it('renders PlayerPanel component', () => {
    render(<GamePage />)
    expect(screen.getByText('PlayerPanel')).toBeInTheDocument()
  })

  it('renders DiceDisplay component', () => {
    render(<GamePage />)
    expect(screen.getByText('DiceDisplay')).toBeInTheDocument()
  })

  it('renders ActionPanel component', () => {
    render(<GamePage />)
    expect(screen.getByText('ActionPanel')).toBeInTheDocument()
  })
})
