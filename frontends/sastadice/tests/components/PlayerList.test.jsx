/**
 * Tests for PlayerList component
 */
import { render, screen } from '@testing-library/react'
import PlayerList from '../../src/components/lobby/PlayerList'

describe('PlayerList', () => {
  it('renders empty state when no players', () => {
    render(<PlayerList players={[]} />)
    expect(screen.getByText(/NO PLAYERS YET/)).toBeInTheDocument()
  })

  it('renders empty state when players is null', () => {
    render(<PlayerList players={null} />)
    expect(screen.getByText(/NO PLAYERS YET/)).toBeInTheDocument()
  })

  it('renders empty state when players is undefined', () => {
    render(<PlayerList players={undefined} />)
    expect(screen.getByText(/NO PLAYERS YET/)).toBeInTheDocument()
  })

  it('renders list of players', () => {
    const players = [
      { id: '1', name: 'Player 1', cash: 1500, color: '#FF6B6B' },
      { id: '2', name: 'Player 2', cash: 2000, color: '#4ECDC4' },
    ]
    render(<PlayerList players={players} />)
    expect(screen.getByText('PLAYER 1')).toBeInTheDocument()
    expect(screen.getByText('PLAYER 2')).toBeInTheDocument()
  })

  it('displays player numbers', () => {
    const players = [
      { id: '1', name: 'Player 1', cash: 1500, color: '#FF6B6B' },
      { id: '2', name: 'Player 2', cash: 2000, color: '#4ECDC4' },
      { id: '3', name: 'Player 3', cash: 1800, color: '#45B7D1' },
    ]
    render(<PlayerList players={players} />)
    expect(screen.getByText('01')).toBeInTheDocument()
    expect(screen.getByText('02')).toBeInTheDocument()
    expect(screen.getByText('03')).toBeInTheDocument()
  })

  it('highlights current player with YOU badge', () => {
    const players = [
      { id: '1', name: 'Player 1', cash: 1500, color: '#FF6B6B' },
      { id: '2', name: 'Player 2', cash: 2000, color: '#4ECDC4' },
    ]
    render(<PlayerList players={players} currentPlayerId="1" />)
    expect(screen.getByText('YOU')).toBeInTheDocument()
  })

  it('shows CPU badge for CPU players', () => {
    const players = [
      { id: '1', name: 'CPU-1', cash: 1500, color: '#FF6B6B' },
    ]
    render(<PlayerList players={players} />)
    expect(screen.getByText('CPU')).toBeInTheDocument()
  })

  it('displays submitted tiles count', () => {
    const players = [
      { id: '1', name: 'Player 1', cash: 1500, color: '#FF6B6B', submitted_tiles: [{}, {}, {}] },
    ]
    render(<PlayerList players={players} />)
    expect(screen.getByText('3 TILES')).toBeInTheDocument()
  })
})
