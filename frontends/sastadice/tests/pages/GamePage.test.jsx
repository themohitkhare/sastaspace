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
vi.mock('../../src/components/game/IsometricContainer', () => ({
  default: ({ children }) => <div>IsometricContainer{children}</div>,
}))
vi.mock('../../src/components/game/TileComponent', () => ({
  default: ({ tile }) => <div>Tile: {tile.name}</div>,
}))
vi.mock('../../src/components/game/PlayerToken', () => ({
  default: ({ player }) => <div>Token: {player.name}</div>,
}))
vi.mock('../../src/components/game/DiceRoller', () => ({
  default: () => <div>DiceRoller</div>,
}))

describe('GamePage', () => {
  const mockGame = {
    id: 'game-123',
    status: 'ACTIVE',
    board_size: 6,
    current_turn_player_id: 'player-1',
    board: [
      { id: 'tile-1', name: 'Tile 1', x: 0, y: 0, position: 0 },
      { id: 'tile-2', name: 'Tile 2', x: 1, y: 0, position: 1 },
    ],
    players: [
      { id: 'player-1', name: 'Player 1', position: 0 },
      { id: 'player-2', name: 'Player 2', position: 1 },
    ],
  }

  beforeEach(() => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: 'game-123',
        game: mockGame,
      }
      return selector(state)
    })
  })

  it('renders game page with game data', () => {
    render(<GamePage />)
    expect(screen.getByText('SASTADICE GAME')).toBeInTheDocument()
    expect(screen.getByText(/Status:/)).toBeInTheDocument()
    expect(screen.getByText(/Turn:/)).toBeInTheDocument()
  })

  it('displays game status', () => {
    render(<GamePage />)
    expect(screen.getByText('ACTIVE')).toBeInTheDocument()
  })

  it('displays current turn player', () => {
    render(<GamePage />)
    expect(screen.getByText('Player 1')).toBeInTheDocument()
  })

  it('renders loading state when game is null', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: 'game-123',
        game: null,
      }
      return selector(state)
    })

    render(<GamePage />)
    expect(screen.getByText('Loading game...')).toBeInTheDocument()
  })

  it('starts polling for game updates', () => {
    render(<GamePage />)
    expect(useSastaPolling).toHaveBeenCalledWith('game-123', 2000)
  })

  it('renders all board tiles', () => {
    render(<GamePage />)
    expect(screen.getByText('Tile: Tile 1')).toBeInTheDocument()
    expect(screen.getByText('Tile: Tile 2')).toBeInTheDocument()
  })

  it('renders all player tokens', () => {
    render(<GamePage />)
    expect(screen.getByText('Token: Player 1')).toBeInTheDocument()
    expect(screen.getByText('Token: Player 2')).toBeInTheDocument()
  })

  it('renders DiceRoller component', () => {
    render(<GamePage />)
    expect(screen.getByText('DiceRoller')).toBeInTheDocument()
  })
})
