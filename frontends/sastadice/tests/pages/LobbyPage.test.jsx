/**
 * Tests for LobbyPage component
 */
import { render } from '@testing-library/react'
import { vi } from 'vitest'
import LobbyPage from '../../src/pages/LobbyPage'
import { useGameStore } from '../../src/store/useGameStore'
import { useWebSocket } from '../../src/hooks/useWebSocket'

vi.mock('../../src/store/useGameStore')
vi.mock('../../src/hooks/useWebSocket')
vi.mock('../../src/components/lobby/LobbyView', () => ({
  default: () => <div>LobbyView</div>,
}))

describe('LobbyPage', () => {
  beforeEach(() => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: 'game-123',
        playerId: 'player-1',
        game: { id: 'game-123', status: 'LOBBY' },
      }
      return selector(state)
    })

    // Mock useWebSocket to return refetch
    useWebSocket.mockReturnValue({ refetch: vi.fn(), connectionLost: false, retry: vi.fn() })
  })

  it('renders LobbyView', () => {
    const { container } = render(<LobbyPage />)
    expect(container.textContent).toContain('LobbyView')
  })

  it('connects WebSocket for game updates', () => {
    render(<LobbyPage />)
    expect(useWebSocket).toHaveBeenCalledWith('game-123', 'player-1')
  })
})
