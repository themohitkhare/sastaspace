import { render, screen, act } from '@testing-library/react'
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import BoardView from '../../src/components/game/BoardView'

const mockTiles = [
  { id: 't1', name: 'GO', x: 0, y: 0, position: 0, type: 'START' },
  { id: 't2', name: 'Tile 1', x: 1, y: 0, position: 1, type: 'PROPERTY' },
  { id: 't3', name: 'Tile 2', x: 2, y: 0, position: 2, type: 'PROPERTY' },
  { id: 't4', name: 'Tile 3', x: 3, y: 0, position: 3, type: 'PROPERTY' },
  { id: 't5', name: 'Tile 4', x: 3, y: 1, position: 4, type: 'PROPERTY' },
  { id: 't6', name: 'Tile 5', x: 3, y: 2, position: 5, type: 'PROPERTY' },
  { id: 't7', name: 'Tile 6', x: 3, y: 3, position: 6, type: 'PROPERTY' },
  { id: 't8', name: 'Tile 7', x: 2, y: 3, position: 7, type: 'PROPERTY' },
  { id: 't9', name: 'Tile 8', x: 1, y: 3, position: 8, type: 'PROPERTY' },
  { id: 't10', name: 'Tile 9', x: 0, y: 3, position: 9, type: 'PROPERTY' },
  { id: 't11', name: 'Tile 10', x: 0, y: 2, position: 10, type: 'PROPERTY' },
  { id: 't12', name: 'Tile 11', x: 0, y: 1, position: 11, type: 'PROPERTY' },
  // Center tile (not on perimeter)
  { id: 'center', name: 'Center', x: 1, y: 1, position: -1, type: 'NEUTRAL' },
]

const mockPlayers = [
  { id: 'p1', name: 'Alice', position: 0, color: '#FF0000' },
  { id: 'p2', name: 'Bob', position: 0, color: '#00FF00' },
]

describe('BoardView', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'innerWidth', { value: 1024, writable: true })
    Object.defineProperty(window, 'innerHeight', { value: 768, writable: true })
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading when boardSize is missing', () => {
    render(<BoardView tiles={mockTiles} />)
    expect(screen.getByText('LOADING BOARD...')).toBeInTheDocument()
  })

  it('renders loading when boardSize is less than 2', () => {
    render(<BoardView tiles={mockTiles} boardSize={1} />)
    expect(screen.getByText('LOADING BOARD...')).toBeInTheDocument()
  })

  it('renders board with tiles', () => {
    render(<BoardView tiles={mockTiles} boardSize={4} players={[]} />)
    expect(screen.getByText('GO')).toBeInTheDocument()
    expect(screen.getByText('TILE 1')).toBeInTheDocument()
  })

  it('does not render non-perimeter tiles', () => {
    render(<BoardView tiles={mockTiles} boardSize={4} players={[]} />)
    expect(screen.queryByText('CENTER')).not.toBeInTheDocument()
  })

  it('renders player tokens', () => {
    render(<BoardView tiles={mockTiles} boardSize={4} players={mockPlayers} />)
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
  })

  it('renders center content when boardSize > 2', () => {
    render(
      <BoardView tiles={mockTiles} boardSize={4} players={[]}>
        <div>Center Content</div>
      </BoardView>
    )
    expect(screen.getByText('Center Content')).toBeInTheDocument()
  })

  it('handles resize events', async () => {
    render(<BoardView tiles={mockTiles} boardSize={4} players={[]} />)

    await act(async () => {
      Object.defineProperty(window, 'innerWidth', { value: 500, writable: true })
      window.dispatchEvent(new Event('resize'))
    })

    // Board should still be rendered
    expect(screen.getByText('GO')).toBeInTheDocument()
  })

  it('handles empty players array', () => {
    render(<BoardView tiles={mockTiles} boardSize={4} />)
    expect(screen.getByText('GO')).toBeInTheDocument()
  })

  it('handles empty tiles array', () => {
    render(<BoardView boardSize={4} players={[]} />)
    expect(screen.queryByText('GO')).not.toBeInTheDocument()
  })

  it('positions players with offset when on same tile', () => {
    const playersOnSameTile = [
      { id: 'p1', name: 'Alice', position: 0, color: '#FF0000' },
      { id: 'p2', name: 'Bob', position: 0, color: '#00FF00' },
      { id: 'p3', name: 'Charlie', position: 0, color: '#0000FF' },
    ]
    render(<BoardView tiles={mockTiles} boardSize={4} players={playersOnSameTile} />)
    expect(screen.getByText('A')).toBeInTheDocument()
    expect(screen.getByText('B')).toBeInTheDocument()
    expect(screen.getByText('C')).toBeInTheDocument()
  })

  it('does not render player token if tile not found', () => {
    const playerWithInvalidPosition = [
      { id: 'p1', name: 'Alice', position: 999, color: '#FF0000' },
    ]
    render(<BoardView tiles={mockTiles} boardSize={4} players={playerWithInvalidPosition} />)
    expect(screen.queryByText('A')).not.toBeInTheDocument()
  })
})
