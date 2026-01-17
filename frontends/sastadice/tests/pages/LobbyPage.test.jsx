/**
 * Tests for LobbyPage component
 */
import { render } from '@testing-library/react'
import { vi } from 'vitest'
import LobbyPage from '../../src/pages/LobbyPage'
import { useGameStore } from '../../src/store/useGameStore'
import { useSastaPolling } from '../../src/hooks/useSastaPolling'

vi.mock('../../src/store/useGameStore')
vi.mock('../../src/hooks/useSastaPolling')
vi.mock('../../src/components/lobby/LobbyView', () => ({
  default: () => <div>LobbyView</div>,
}))

describe('LobbyPage', () => {
  beforeEach(() => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: 'game-123',
        game: { id: 'game-123', status: 'LOBBY' },
      }
      return selector(state)
    })
  })

  it('renders LobbyView', () => {
    const { container } = render(<LobbyPage />)
    expect(container.textContent).toContain('LobbyView')
  })

  it('starts polling for game updates', () => {
    render(<LobbyPage />)
    expect(useSastaPolling).toHaveBeenCalledWith('game-123', 2000)
  })
})
