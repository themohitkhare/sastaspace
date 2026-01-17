/**
 * Tests for PlayerList component
 */
import { render, screen } from '@testing-library/react'
import PlayerList from '../../src/components/lobby/PlayerList'

describe('PlayerList', () => {
  it('renders empty state when no players', () => {
    render(<PlayerList players={[]} />)
    expect(screen.getByText('No players yet...')).toBeInTheDocument()
  })

  it('renders empty state when players is null', () => {
    render(<PlayerList players={null} />)
    expect(screen.getByText('No players yet...')).toBeInTheDocument()
  })

  it('renders empty state when players is undefined', () => {
    render(<PlayerList players={undefined} />)
    expect(screen.getByText('No players yet...')).toBeInTheDocument()
  })

  it('renders list of players', () => {
    const players = [
      { id: '1', name: 'Player 1', cash: 1500 },
      { id: '2', name: 'Player 2', cash: 2000 },
    ]
    render(<PlayerList players={players} />)
    expect(screen.getByText('PLAYERS (2)')).toBeInTheDocument()
    expect(screen.getByText('Player 1')).toBeInTheDocument()
    expect(screen.getByText('Player 2')).toBeInTheDocument()
    expect(screen.getByText('Cash: $1500')).toBeInTheDocument()
    expect(screen.getByText('Cash: $2000')).toBeInTheDocument()
  })

  it('displays correct player count', () => {
    const players = [
      { id: '1', name: 'Player 1', cash: 1500 },
      { id: '2', name: 'Player 2', cash: 2000 },
      { id: '3', name: 'Player 3', cash: 1800 },
    ]
    render(<PlayerList players={players} />)
    expect(screen.getByText('PLAYERS (3)')).toBeInTheDocument()
  })

  it('renders player with different cash amounts', () => {
    const players = [
      { id: '1', name: 'Rich Player', cash: 5000 },
      { id: '2', name: 'Poor Player', cash: 500 },
    ]
    render(<PlayerList players={players} />)
    expect(screen.getByText('Cash: $5000')).toBeInTheDocument()
    expect(screen.getByText('Cash: $500')).toBeInTheDocument()
  })
})
