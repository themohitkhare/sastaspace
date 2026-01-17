import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import DiceDisplay from '../../src/components/game/DiceDisplay'

describe('DiceDisplay', () => {
  it('renders placeholder when no dice roll', () => {
    render(<DiceDisplay lastDiceRoll={null} />)
    expect(screen.getByText('NO ROLL YET')).toBeInTheDocument()
    expect(screen.getAllByText('?')).toHaveLength(2)
  })

  it('renders dice values when roll is provided', () => {
    const diceRoll = {
      dice1: 3,
      dice2: 4,
      total: 7,
      is_doubles: false,
    }
    render(<DiceDisplay lastDiceRoll={diceRoll} />)
    expect(screen.getByText(/TOTAL: 7/)).toBeInTheDocument()
  })

  it('highlights doubles', () => {
    const diceRoll = {
      dice1: 5,
      dice2: 5,
      total: 10,
      is_doubles: true,
    }
    render(<DiceDisplay lastDiceRoll={diceRoll} />)
    expect(screen.getByText(/DOUBLES!/)).toBeInTheDocument()
  })

  it('shows passed GO bonus', () => {
    const diceRoll = {
      dice1: 6,
      dice2: 6,
      total: 12,
      is_doubles: true,
      passed_go: 200,
    }
    render(<DiceDisplay lastDiceRoll={diceRoll} />)
    expect(screen.getByText(/PASSED GO! \+\$200/)).toBeInTheDocument()
  })

  it('handles undefined lastDiceRoll', () => {
    render(<DiceDisplay />)
    expect(screen.getByText('NO ROLL YET')).toBeInTheDocument()
  })

  it('handles roll without dice1', () => {
    render(<DiceDisplay lastDiceRoll={{}} />)
    expect(screen.getByText('NO ROLL YET')).toBeInTheDocument()
  })
})
