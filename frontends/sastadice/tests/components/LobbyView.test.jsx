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
    expect(screen.getByText('GAME LOBBY')).toBeInTheDocument()
  })

  it('renders join form when not joined', () => {
    render(<LobbyView />)
    expect(screen.getByRole('heading', { name: /JOIN GAME/i })).toBeInTheDocument()
  })

  it('shows join form when player not in game', () => {
    render(<LobbyView />)
    expect(screen.getByText('JOIN GAME')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Enter your name')).toBeInTheDocument()
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
    expect(screen.getByText(/YOUR STATION/)).toBeInTheDocument()
  })

  it('allows joining game with valid name', async () => {
    const user = userEvent.setup()
    render(<LobbyView />)

    const nameInput = screen.getByPlaceholderText('Enter your name')
    await user.type(nameInput, 'Test Player')

    const joinButton = screen.getByRole('button', { name: /JOIN GAME/i })
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

  it('shows alert when joining without name', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    const user = userEvent.setup()
    render(<LobbyView />)

    // Try to join without entering a name
    const joinButton = screen.getByRole('button', { name: /JOIN GAME/i })
    
    // Button should be disabled when name is empty
    expect(joinButton).toBeDisabled()
    
    alertSpy.mockRestore()
  })

  it('handles join errors', async () => {
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    window.alert = vi.fn()
    apiClient.post = vi.fn().mockRejectedValue(new Error('Join failed'))

    const user = userEvent.setup()
    render(<LobbyView />)

    const nameInput = screen.getByPlaceholderText('Enter your name')
    await user.type(nameInput, 'Test Player')

    const joinButton = screen.getByRole('button', { name: /JOIN GAME/i })
    await user.click(joinButton)

    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith('Failed to join game')
    })

    consoleError.mockRestore()
  })

  it('shows start button when player has joined', () => {
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
    expect(screen.getByText(/LAUNCH CONTROL/i)).toBeInTheDocument()
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
    window.alert = vi.fn()
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
      expect(window.alert).toHaveBeenCalledWith('Failed to toggle ready')
    })
  })
})
