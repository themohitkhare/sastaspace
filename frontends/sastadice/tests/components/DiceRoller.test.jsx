/**
 * Tests for DiceRoller component
 */
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, beforeEach } from 'vitest'
import DiceRoller from '../../src/components/game/DiceRoller'
import { useGameStore } from '../../src/store/useGameStore'
import { apiClient } from '../../src/api/apiClient'

vi.mock('../../src/api/apiClient')
vi.mock('../../src/store/useGameStore')

describe('DiceRoller', () => {
  const mockSetIsRolling = vi.fn()
  let mockGameId = 'game-123'
  let mockPlayerId = 'player-123'
  let mockIsMyTurn = true

  beforeEach(() => {
    vi.clearAllMocks()
    useGameStore.mockImplementation((selector) => {
      const state = {
        gameId: mockGameId,
        playerId: mockPlayerId,
        isMyTurn: () => mockIsMyTurn,
      }
      return selector(state)
    })
    apiClient.post = vi.fn().mockResolvedValue({ data: {} })
  })

  it('renders roll dice button when it is my turn', () => {
    mockIsMyTurn = true
    render(<DiceRoller />)
    expect(screen.getByText('ROLL DICE')).toBeInTheDocument()
  })

  it('renders waiting message when it is not my turn', () => {
    mockIsMyTurn = false
    render(<DiceRoller />)
    expect(screen.getByText('Waiting for your turn...')).toBeInTheDocument()
    expect(screen.queryByText('ROLL DICE')).not.toBeInTheDocument()
  })

  it('calls API when roll button is clicked', async () => {
    mockIsMyTurn = true
    const user = userEvent.setup()
    render(<DiceRoller />)

    const button = screen.getByText('ROLL DICE')
    await user.click(button)

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/sastadice/games/game-123/action?player_id=player-123',
        {
          type: 'ROLL_DICE',
          payload: {},
        }
      )
    })
  })

  it('disables button while rolling', async () => {
    mockIsMyTurn = true
    apiClient.post = vi.fn().mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)))
    const user = userEvent.setup()
    render(<DiceRoller />)

    const button = screen.getByText('ROLL DICE')
    await user.click(button)

    expect(screen.getByText('ROLLING...')).toBeInTheDocument()
    expect(button).toBeDisabled()
  })

  it('does not call API if gameId is missing', async () => {
    mockIsMyTurn = true
    mockGameId = null
    const user = userEvent.setup()
    render(<DiceRoller />)

    const button = screen.getByText('ROLL DICE')
    await user.click(button)

    await waitFor(() => {
      expect(apiClient.post).not.toHaveBeenCalled()
    })
  })

  it('does not call API if playerId is missing', async () => {
    mockIsMyTurn = true
    mockPlayerId = null
    const user = userEvent.setup()
    render(<DiceRoller />)

    const button = screen.getByText('ROLL DICE')
    await user.click(button)

    await waitFor(() => {
      expect(apiClient.post).not.toHaveBeenCalled()
    })
  })

  it('handles API errors gracefully', async () => {
    mockIsMyTurn = true
    mockGameId = 'game-123'
    mockPlayerId = 'player-123'
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})
    const error = new Error('API Error')
    
    // Use mockRejectedValue to properly reject the promise
    apiClient.post = vi.fn().mockRejectedValue(error)
    
    const user = userEvent.setup()
    const { container } = render(<DiceRoller />)

    const button = screen.getByText('ROLL DICE')
    
    // Click button
    await user.click(button)

    // Wait for API call to be made
    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalled()
    }, { timeout: 1000 })

    // Wait for error handling - the catch block should execute
    // We verify the component doesn't crash and the error is handled
    await new Promise(resolve => setTimeout(resolve, 300))

    // Component should still be rendered (error was caught)
    expect(container).toBeInTheDocument()
    // Verify API was called (error handling is internal to component)
    expect(apiClient.post).toHaveBeenCalled()
    // Component should handle error gracefully without crashing
    expect(screen.queryByText('ROLL DICE')).toBeInTheDocument()
    consoleError.mockRestore()
  })
})
