import { render, screen, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import DiceDisplay from '../../src/components/game/DiceDisplay'

describe('DiceDisplay', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.runOnlyPendingTimers()
    vi.useRealTimers()
  })

  it('renders placeholder when no dice roll', () => {
    render(<DiceDisplay lastDiceRoll={null} />)
    expect(screen.getByText('WAITING FOR ROLL')).toBeInTheDocument()
    expect(screen.getAllByText('?')).toHaveLength(2)
  })

  it('handles undefined lastDiceRoll', () => {
    render(<DiceDisplay />)
    expect(screen.getByText('WAITING FOR ROLL')).toBeInTheDocument()
  })

  it('handles roll without dice1', () => {
    render(<DiceDisplay lastDiceRoll={{}} />)
    expect(screen.getByText('WAITING FOR ROLL')).toBeInTheDocument()
  })

  it('renders dice values when roll is provided', () => {
    const diceRoll = {
      dice1: 3,
      dice2: 4,
      total: 7,
      is_doubles: false,
    }
    render(<DiceDisplay lastDiceRoll={diceRoll} />)

    // Initially shows "ROLLING..." during animation
    expect(screen.getByText('ROLLING...')).toBeInTheDocument()

    // After animation completes
    act(() => {
      vi.advanceTimersByTime(700)
    })

    expect(screen.getByText(/TOTAL: 7/)).toBeInTheDocument()
  })

  it('highlights doubles after animation', () => {
    const diceRoll = {
      dice1: 5,
      dice2: 5,
      total: 10,
      is_doubles: true,
    }
    render(<DiceDisplay lastDiceRoll={diceRoll} />)

    // After animation completes
    act(() => {
      vi.advanceTimersByTime(700)
    })

    expect(screen.getByText(/DOUBLES/)).toBeInTheDocument()
  })

  it('shows passed GO bonus after animation', () => {
    const diceRoll = {
      dice1: 6,
      dice2: 6,
      total: 12,
      is_doubles: true,
      passed_go: 200,
    }
    render(<DiceDisplay lastDiceRoll={diceRoll} />)

    // After animation completes
    act(() => {
      vi.advanceTimersByTime(700)
    })

    expect(screen.getByText(/PASSED GO/)).toBeInTheDocument()
  })
})
