/**
 * Tests for LobbyView component
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, beforeEach } from 'vitest'
import LobbyView from '../../src/components/lobby/LobbyView'
import { useGameStore } from '../../src/store/useGameStore'
import { apiClient } from '../../src/api/apiClient'

vi.mock('../../src/store/useGameStore')
vi.mock('../../src/api/apiClient')
vi.mock('../../src/components/lobby/LaunchKey', () => ({
  default: ({ isReady, onToggle }) => (
    <button onClick={onToggle} aria-label="Turn key to ready up">
      LaunchKey: {isReady ? 'READY' : 'NOT READY'}
    </button>
  ),
}))
vi.mock('../../src/components/lobby/KeyStatus', () => ({
  default: ({ player, isMe }) => (
    <div>KeyStatus: {player.name} {isMe ? '(YOU)' : ''}</div>
  ),
}))
vi.mock('../../src/components/lobby/TileSubmissionForm', () => ({
  default: ({ tiles, setTiles }) => (
    <div data-testid="tile-submission-form">TILES ({tiles?.length || 0}/5)</div>
  ),
}))

describe('LobbyView', () => {
  let mockGameId
  let mockGame
  let mockSetPlayerId
  let mockSetGame

  beforeEach(() => {
    vi.clearAllMocks()

    mockGameId = 'game-123'
    mockGame = {
      id: 'game-123',
      status: 'LOBBY',
      players: [],
    }
    mockSetPlayerId = vi.fn()
    mockSetGame = vi.fn()

    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        game: mockGame,
        playerId: null,
        setPlayerId: mockSetPlayerId,
        setGame: mockSetGame,
      }
      return selector(state)
    })

    apiClient.post = vi.fn().mockResolvedValue({
      data: { id: 'player-123', name: 'Test Player' },
    })

    apiClient.get = vi.fn().mockResolvedValue({
      data: { game: mockGame, version: 1 },
    })
  })

  it('renders lobby heading', () => {
    render(<LobbyView />)
    expect(screen.getByText('SASTADICE')).toBeInTheDocument()
  })

  it('renders join form when not joined', () => {
    render(<LobbyView />)
    expect(screen.getByText(/AUTHENTICATE_OPERATOR/i)).toBeInTheDocument()
  })

  it('shows join form when player not in game', () => {
    render(<LobbyView />)
    expect(screen.getByText(/AUTHENTICATE_OPERATOR/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText('CODENAME')).toBeInTheDocument()
  })

  it('shows waiting message when player already joined', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        game: {
          ...mockGame,
          players: [{ id: 'player-123', name: 'Test Player' }],
        },
        playerId: 'player-123',
        setPlayerId: mockSetPlayerId,
        setGame: mockSetGame,
      }
      return selector(state)
    })

    render(<LobbyView />)
    expect(screen.getByText('YOU')).toBeInTheDocument()
  })

  it('allows joining game with valid name', async () => {
    const user = userEvent.setup()
    render(<LobbyView />)

    const nameInput = screen.getByPlaceholderText('CODENAME')
    await user.type(nameInput, 'Test Player')

    const joinButton = screen.getByRole('button', { name: /INIT_CONNECTION/i })
    await user.click(joinButton)

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/sastadice/games/game-123/join',
        expect.objectContaining({
          name: 'Test Player',
        })
      )
    })
  })

  it('join button is disabled when name is empty', async () => {
    render(<LobbyView />)

    const joinButton = screen.getByRole('button', { name: /INIT_CONNECTION/i })
    expect(joinButton).toBeDisabled()
  })

  it('handles join errors', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => { })
    apiClient.post = vi.fn().mockRejectedValue(new Error('Join failed'))

    const user = userEvent.setup()
    render(<LobbyView />)

    const nameInput = screen.getByPlaceholderText('CODENAME')
    await user.type(nameInput, 'Test Player')

    const joinButton = screen.getByRole('button', { name: /INIT_CONNECTION/i })
    await user.click(joinButton)

    await waitFor(() => {
      expect(screen.getByText('Failed to join game')).toBeInTheDocument()
    })

    consoleError.mockRestore()
  })

  it('shows launch control section when player has joined', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        game: {
          ...mockGame,
          players: [{ id: 'player-1', name: 'Player 1' }],
        },
        playerId: 'player-1',
        setPlayerId: mockSetPlayerId,
        setGame: mockSetGame,
      }
      return selector(state)
    })

    render(<LobbyView />)
    expect(screen.getByText(/LAUNCH_SEQUENCE/i)).toBeInTheDocument()
  })

  it('allows toggling ready state via launch key', async () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        game: {
          ...mockGame,
          players: [
            { id: 'player-1', name: 'Player 1', ready: false, color: '#FF0000' },
            { id: 'player-2', name: 'Player 2', ready: false, color: '#00FF00' },
          ],
        },
        playerId: 'player-1',
        setPlayerId: mockSetPlayerId,
        setGame: mockSetGame,
      }
      return selector(state)
    })

    const user = userEvent.setup()
    render(<LobbyView onRefresh={vi.fn()} />)

    const launchKey = screen.getByRole('button', { name: /Turn key to ready up/i })
    await user.click(launchKey)

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/sastadice/games/game-123/ready/player-1')
    })
  })

  it('handles toggle ready errors', async () => {
    apiClient.post = vi.fn().mockRejectedValue(new Error('Ready failed'))

    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        game: {
          ...mockGame,
          players: [
            { id: 'player-1', name: 'Player 1', ready: false, color: '#FF0000' },
            { id: 'player-2', name: 'Player 2', ready: false, color: '#00FF00' },
          ],
        },
        playerId: 'player-1',
        setPlayerId: mockSetPlayerId,
        setGame: mockSetGame,
      }
      return selector(state)
    })

    const user = userEvent.setup()
    render(<LobbyView />)

    const launchKey = screen.getByRole('button', { name: /Turn key to ready up/i })
    await user.click(launchKey)

    await waitFor(() => {
      expect(screen.getByText('Failed to toggle ready')).toBeInTheDocument()
    })
  })

  // === ANCHOR PATTERN LAYOUT TESTS ===

  it('renders access code section', () => {
    render(<LobbyView />)
    expect(screen.getByText('ACCESS_KEY')).toBeInTheDocument()
    expect(screen.getByText('GAME-123')).toBeInTheDocument()
  })

  it('renders COPY button for game code', () => {
    render(<LobbyView />)
    expect(screen.getByText('COPY_ACCESS_KEY')).toBeInTheDocument()
  })

  it('renders RULES button', () => {
    render(<LobbyView />)
    expect(screen.getByText(/REQ_INTEL/)).toBeInTheDocument()
  })

  it('displays connected players count', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        game: {
          ...mockGame,
          players: [
            { id: 'player-1', name: 'Player 1', ready: false, color: '#FF0000' },
          ],
        },
        playerId: 'player-1',
        setPlayerId: mockSetPlayerId,
        setGame: mockSetGame,
      }
      return selector(state)
    })

    render(<LobbyView />)
    expect(screen.getByText('01')).toBeInTheDocument() // Adjusted to expect '01' based on rendered output
  })

  it('shows launch control section when player has joined', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        game: {
          ...mockGame,
          players: [{ id: 'player-1', name: 'Player 1', ready: false, color: '#FF0000' }],
        },
        playerId: 'player-1',
        setPlayerId: mockSetPlayerId,
        setGame: mockSetGame,
      }
      return selector(state)
    })

    render(<LobbyView />)
    expect(screen.getByText('LAUNCH_SEQUENCE')).toBeInTheDocument()
  })

  it('displays armed count in launch control', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        game: {
          ...mockGame,
          players: [
            { id: 'player-1', name: 'Player 1', ready: true, color: '#FF0000' },
            { id: 'player-2', name: 'Player 2', ready: false, color: '#00FF00' },
          ],
        },
        playerId: 'player-1',
        setPlayerId: mockSetPlayerId,
        setGame: mockSetGame,
      }
      return selector(state)
    })

    render(<LobbyView />)
    expect(screen.getByText('1/2 ARMED')).toBeInTheDocument()
  })

  it('shows all armed message when everyone is ready', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        game: {
          ...mockGame,
          players: [
            { id: 'player-1', name: 'Player 1', ready: true, color: '#FF0000' },
            { id: 'player-2', name: 'Player 2', ready: true, color: '#00FF00' },
          ],
        },
        playerId: 'player-1',
        setPlayerId: mockSetPlayerId,
        setGame: mockSetGame,
      }
      return selector(state)
    })

    render(<LobbyView />)
    expect(screen.getByText(/LAUNCH IMMINENT/)).toBeInTheDocument()
  })

  it('shows host crown indicator for host player', () => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        game: {
          ...mockGame,
          host_id: 'player-1',
          players: [{ id: 'player-1', name: 'Player 1', ready: false, color: '#FF0000' }],
        },
        playerId: 'player-1',
        setPlayerId: mockSetPlayerId,
        setGame: mockSetGame,
      }
      return selector(state)
    })

    render(<LobbyView />)
    expect(screen.getAllByText('CMD')[0]).toBeInTheDocument()
  })

  describe('TileSubmissionForm integration', () => {
    it('shows tile submission form when board preset is UGC_24 and player has joined', () => {
      useGameStore.mockImplementation((selector) => {
        const state = {
          gameId: 'game-123',
          game: {
            id: 'game-123',
            status: 'LOBBY',
            players: [{ id: 'player-123', name: 'Test Player', ready: false, color: '#00ff00' }],
            settings: { board_preset: 'UGC_24' },
          },
          playerId: 'player-123',
          setPlayerId: vi.fn(),
          setGame: vi.fn(),
        }
        return selector(state)
      })

      render(<LobbyView />)
      expect(screen.getByText(/TILES/i)).toBeInTheDocument()
    })

    it('hides tile submission form when board preset is CLASSIC', () => {
      useGameStore.mockImplementation((selector) => {
        const state = {
          gameId: 'game-123',
          game: {
            id: 'game-123',
            status: 'LOBBY',
            players: [{ id: 'player-123', name: 'Test Player', ready: false, color: '#00ff00' }],
            settings: { board_preset: 'CLASSIC' },
          },
          playerId: 'player-123',
          setPlayerId: vi.fn(),
          setGame: vi.fn(),
        }
        return selector(state)
      })

      render(<LobbyView />)
      expect(screen.queryByTestId('tile-submission-form')).not.toBeInTheDocument()
    })
  })
})
