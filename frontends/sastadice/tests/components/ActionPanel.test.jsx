import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import ActionPanel from '../../src/components/game/ActionPanel'

vi.mock('../../src/api/apiClient', () => ({
  default: {
    post: vi.fn(),
  },
}))

import apiClient from '../../src/api/apiClient'

describe('ActionPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows roll dice button in PRE_ROLL phase when it is my turn', () => {
    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="PRE_ROLL"
        isMyTurn={true}
      />
    )
    expect(screen.getByText('> ROLL DICE')).toBeInTheDocument()
  })

  it('shows waiting message when not my turn', () => {
    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="PRE_ROLL"
        isMyTurn={false}
      />
    )
    expect(screen.getByText('WAITING FOR OTHER PLAYER...')).toBeInTheDocument()
  })

  it('shows end turn button in POST_TURN phase when it is my turn', () => {
    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="POST_TURN"
        isMyTurn={true}
      />
    )
    expect(screen.getByText('> END TURN')).toBeInTheDocument()
  })

  it('shows buy/pass buttons in DECISION phase with BUY pending', () => {
    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="DECISION"
        pendingDecision={{ type: 'BUY', price: 200 }}
        isMyTurn={true}
      />
    )
    expect(screen.getByText('BUY FOR $200?')).toBeInTheDocument()
    expect(screen.getByText('BUY $200')).toBeInTheDocument()
    expect(screen.getByText('PASS')).toBeInTheDocument()
  })

  it('displays last event message', () => {
    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="POST_TURN"
        isMyTurn={true}
        lastEventMessage="You landed on Go!"
      />
    )
    expect(screen.getByText('You landed on Go!')).toBeInTheDocument()
  })

  it('calls API and onActionComplete when roll dice clicked', async () => {
    const onActionComplete = vi.fn()
    apiClient.post.mockResolvedValueOnce({ data: { success: true } })

    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="PRE_ROLL"
        isMyTurn={true}
        onActionComplete={onActionComplete}
      />
    )

    fireEvent.click(screen.getByText('> ROLL DICE'))

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/sastadice/games/game-1/action?player_id=player-1',
        { type: 'ROLL_DICE', payload: {} }
      )
      expect(onActionComplete).toHaveBeenCalledWith({ success: true })
    })
  })

  it('shows error when API returns success: false', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { success: false, message: 'Invalid move' } })

    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="PRE_ROLL"
        isMyTurn={true}
      />
    )

    fireEvent.click(screen.getByText('> ROLL DICE'))

    await waitFor(() => {
      expect(screen.getByText('Invalid move')).toBeInTheDocument()
    })
  })

  it('shows error when API throws with string detail', async () => {
    apiClient.post.mockRejectedValueOnce({
      response: { data: { detail: 'Something went wrong' } }
    })

    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="PRE_ROLL"
        isMyTurn={true}
      />
    )

    fireEvent.click(screen.getByText('> ROLL DICE'))

    await waitFor(() => {
      expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    })
  })

  it('shows error when API throws with array detail', async () => {
    apiClient.post.mockRejectedValueOnce({
      response: { data: { detail: [{ msg: 'Error 1' }, { msg: 'Error 2' }] } }
    })

    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="PRE_ROLL"
        isMyTurn={true}
      />
    )

    fireEvent.click(screen.getByText('> ROLL DICE'))

    await waitFor(() => {
      expect(screen.getByText('Error 1, Error 2')).toBeInTheDocument()
    })
  })

  it('shows error when API throws with message only', async () => {
    apiClient.post.mockRejectedValueOnce({ message: 'Network Error' })

    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="PRE_ROLL"
        isMyTurn={true}
      />
    )

    fireEvent.click(screen.getByText('> ROLL DICE'))

    await waitFor(() => {
      expect(screen.getByText('Network Error')).toBeInTheDocument()
    })
  })

  it('does not call API if gameId is missing', async () => {
    render(
      <ActionPanel
        playerId="player-1"
        turnPhase="PRE_ROLL"
        isMyTurn={true}
      />
    )

    fireEvent.click(screen.getByText('> ROLL DICE'))

    await waitFor(() => {
      expect(apiClient.post).not.toHaveBeenCalled()
    })
  })

  it('does not call API if playerId is missing', async () => {
    render(
      <ActionPanel
        gameId="game-1"
        turnPhase="PRE_ROLL"
        isMyTurn={true}
      />
    )

    fireEvent.click(screen.getByText('> ROLL DICE'))

    await waitFor(() => {
      expect(apiClient.post).not.toHaveBeenCalled()
    })
  })

  it('calls buy property API', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { success: true } })

    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="DECISION"
        pendingDecision={{ type: 'BUY', price: 200 }}
        isMyTurn={true}
      />
    )

    fireEvent.click(screen.getByText('BUY $200'))

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/sastadice/games/game-1/action?player_id=player-1',
        { type: 'BUY_PROPERTY', payload: {} }
      )
    })
  })

  it('calls pass property API', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { success: true } })

    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="DECISION"
        pendingDecision={{ type: 'BUY', price: 200 }}
        isMyTurn={true}
      />
    )

    fireEvent.click(screen.getByText('PASS'))

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/sastadice/games/game-1/action?player_id=player-1',
        { type: 'PASS_PROPERTY', payload: {} }
      )
    })
  })

  it('calls end turn API', async () => {
    apiClient.post.mockResolvedValueOnce({ data: { success: true } })

    render(
      <ActionPanel
        gameId="game-1"
        playerId="player-1"
        turnPhase="POST_TURN"
        isMyTurn={true}
      />
    )

    fireEvent.click(screen.getByText('> END TURN'))

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith(
        '/sastadice/games/game-1/action?player_id=player-1',
        { type: 'END_TURN', payload: {} }
      )
    })
  })
})
