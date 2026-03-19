import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import PlayerPanel from '../../src/components/game/PlayerPanel'

const mockPlayers = [
  { id: 'p1', name: 'Alice', cash: 1500, color: '#FF0000' },
  { id: 'p2', name: 'Bob', cash: 1200, color: '#00FF00' },
]

const mockTiles = [
  { id: 't1', name: 'Boardwalk', owner_id: 'p1' },
  { id: 't2', name: 'Park Place', owner_id: 'p1' },
  { id: 't3', name: 'Atlantic', owner_id: 'p1' },
  { id: 't4', name: 'Ventnor', owner_id: 'p1' },
  { id: 't5', name: 'Baltic', owner_id: 'p2' },
]

describe('PlayerPanel', () => {
  it('renders player names', () => {
    render(<PlayerPanel players={mockPlayers} />)
    expect(screen.getByText('ALICE')).toBeInTheDocument()
    expect(screen.getByText('BOB')).toBeInTheDocument()
  })

  it('renders player cash values', () => {
    render(<PlayerPanel players={mockPlayers} />)
    expect(screen.getByText('$1,500')).toBeInTheDocument()
    expect(screen.getByText('$1,200')).toBeInTheDocument()
  })

  it('renders player initial in colored box', () => {
    render(<PlayerPanel players={mockPlayers} />)
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
  })

  it('shows YOU badge for current player', () => {
    render(
      <PlayerPanel 
        players={mockPlayers} 
        currentPlayerId="p1"
      />
    )
    expect(screen.getByText('YOU')).toBeInTheDocument()
  })

  it('shows turn indicator for current turn player', () => {
    render(
      <PlayerPanel 
        players={mockPlayers} 
        currentTurnPlayerId="p2"
      />
    )
    expect(screen.getByText('>>')).toBeInTheDocument()
  })

  it('renders owned tiles for players', () => {
    render(
      <PlayerPanel 
        players={mockPlayers} 
        tiles={mockTiles}
      />
    )
    expect(screen.getByText('BOARDW')).toBeInTheDocument()
    expect(screen.getByText('BALTIC')).toBeInTheDocument()
  })

  it('shows +N indicator when player owns more than 3 tiles', () => {
    render(
      <PlayerPanel 
        players={mockPlayers} 
        tiles={mockTiles}
      />
    )
    expect(screen.getByText('+1')).toBeInTheDocument()
  })

  it('renders empty state when no players', () => {
    render(<PlayerPanel />)
    expect(screen.getByText('PLAYERS')).toBeInTheDocument()
  })

  it('highlights current turn player with accent background', () => {
    const { container } = render(
      <PlayerPanel
        players={mockPlayers}
        currentTurnPlayerId="p1"
      />
    )
    const playerDiv = container.querySelector('.bg-sasta-accent')
    expect(playerDiv).toBeInTheDocument()
  })
})

describe('Buff badges', () => {
  it('shows VPN badge when player has VPN buff', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000', active_buff: 'VPN' },
    ]
    render(
      <PlayerPanel players={players} currentTurnPlayerId="p1" currentPlayerId="p1" tiles={[]} turnPhase="PRE_ROLL" />
    )
    expect(screen.getByText('VPN')).toBeInTheDocument()
  })

  it('shows DDOS badge when player has DDOS buff', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000', active_buff: 'DDOS' },
    ]
    render(
      <PlayerPanel players={players} currentTurnPlayerId="p1" currentPlayerId="p1" tiles={[]} turnPhase="PRE_ROLL" />
    )
    expect(screen.getByText('DDOS')).toBeInTheDocument()
  })

  it('shows no buff badge when active_buff is null', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000', active_buff: null },
    ]
    render(
      <PlayerPanel players={players} currentTurnPlayerId="p1" currentPlayerId="p1" tiles={[]} turnPhase="PRE_ROLL" />
    )
    expect(screen.queryByText('VPN')).not.toBeInTheDocument()
    expect(screen.queryByText('DDOS')).not.toBeInTheDocument()
    expect(screen.queryByText('PEEK')).not.toBeInTheDocument()
  })
})

describe('PlayerPanel spectator mode', () => {
  it('hides trade buttons when onTradeClick is null', () => {
    const players = [
      { id: 'p1', name: 'Alice', cash: 1000, properties: [], color: '#ff0000' },
      { id: 'p2', name: 'Bob', cash: 500, properties: [], color: '#00ff00' },
    ]
    render(
      <PlayerPanel
        players={players}
        currentTurnPlayerId="p1"
        currentPlayerId="p1"
        tiles={[]}
        onTradeClick={null}
        turnPhase="PRE_ROLL"
      />
    )
    expect(screen.queryByText('TRADE')).toBeNull()
  })
})
