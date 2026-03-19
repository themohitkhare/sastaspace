import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import CenterStage from '../../src/components/game/CenterStage'

vi.mock('../../src/components/game/DiceDisplay', () => ({ default: () => <div>DiceDisplay</div> }))
vi.mock('../../src/components/game/CenterActionButton', () => ({ default: () => <div>CenterActionButton</div> }))
vi.mock('../../src/components/game/TileCard', () => ({ default: () => null }))
vi.mock('../../src/components/game/EventToast', () => ({ default: () => null }))

const baseProps = {
  lastDiceRoll: null, gameId: 'g1', playerId: 'p1', turnPhase: 'PRE_ROLL',
  pendingDecision: null, isMyTurn: true, isCpuTurn: false,
  currentPlayer: { id: 'p1', name: 'Alice', color: '#ff0000' },
  currentTile: null, tileOwner: null, myPlayerCash: 1500, lastEventMessage: null,
  onActionComplete: vi.fn(), myPlayer: { id: 'p1', name: 'Alice', cash: 1500 },
  onDdosActivate: vi.fn(), onManageProperties: vi.fn(),
  hasUpgradeableProperties: false, board: [], players: [],
  eventDeckSize: 23, rentMultiplier: 1.0,
}

describe('CenterStage', () => {
  it('shows event deck counter', () => {
    render(<CenterStage {...baseProps} eventDeckSize={23} />)
    expect(screen.getByText('DECK: 23/35')).toBeDefined()
  })

  it('shows MARKET CRASH when rent multiplier below 1', () => {
    render(<CenterStage {...baseProps} rentMultiplier={0.5} />)
    expect(screen.getByText(/MARKET CRASH/)).toBeDefined()
  })

  it('shows BULL MARKET when rent multiplier above 1', () => {
    render(<CenterStage {...baseProps} rentMultiplier={1.5} />)
    expect(screen.getByText(/BULL MARKET/)).toBeDefined()
  })

  it('shows no economy indicator when rent multiplier is 1.0', () => {
    render(<CenterStage {...baseProps} rentMultiplier={1.0} />)
    expect(screen.queryByText(/MARKET/)).toBeNull()
  })
})
