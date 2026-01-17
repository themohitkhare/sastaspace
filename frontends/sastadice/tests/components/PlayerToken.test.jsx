/**
 * Tests for PlayerToken component
 */
import { render } from '@testing-library/react'
import PlayerToken from '../../src/components/game/PlayerToken'

describe('PlayerToken', () => {
  const mockPlayer = {
    id: 'player-1',
    name: 'Test Player',
    cash: 1500,
    position: 0,
    color: '#FF6B6B',
  }

  const mockTile = { id: 'tile-1', position: 0, x: 0, y: 0 }

  it('renders player token on perimeter tile', () => {
    const { container } = render(
      <PlayerToken
        player={mockPlayer}
        tile={mockTile}
        boardSize={4}
      />
    )
    expect(container.querySelector('.player-token')).toBeInTheDocument()
  })

  it('returns null when tile is null', () => {
    const { container } = render(
      <PlayerToken
        player={mockPlayer}
        tile={null}
        boardSize={4}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it('returns null when tile is not on perimeter', () => {
    const innerTile = { id: 'tile-1', position: 0, x: 1, y: 1 }
    const { container } = render(
      <PlayerToken
        player={mockPlayer}
        tile={innerTile}
        boardSize={4}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it('displays player initial', () => {
    const { container } = render(
      <PlayerToken
        player={mockPlayer}
        tile={mockTile}
        boardSize={4}
      />
    )
    expect(container.textContent).toContain('T')
  })

  it('uses player color for background', () => {
    const { container } = render(
      <PlayerToken
        player={mockPlayer}
        tile={mockTile}
        boardSize={4}
      />
    )
    const token = container.querySelector('.player-token')
    expect(token).toHaveStyle({ backgroundColor: '#FF6B6B' })
  })

  it('handles tiles on different perimeter edges', () => {
    const perimeterTiles = [
      { id: 'tile-1', position: 0, x: 0, y: 0 },      // top-left
      { id: 'tile-2', position: 1, x: 3, y: 0 },      // top-right
      { id: 'tile-3', position: 2, x: 0, y: 3 },      // bottom-left
      { id: 'tile-4', position: 3, x: 3, y: 3 },      // bottom-right
    ]

    perimeterTiles.forEach((tile) => {
      const { container, unmount } = render(
        <PlayerToken
          player={mockPlayer}
          tile={tile}
          boardSize={4}
        />
      )
      expect(container.querySelector('.player-token')).toBeInTheDocument()
      unmount()
    })
  })

  it('applies offset for multiple players on same tile', () => {
    const { container } = render(
      <PlayerToken
        player={mockPlayer}
        tile={mockTile}
        boardSize={4}
        offsetX={10}
        offsetY={-10}
      />
    )
    expect(container.querySelector('.player-token')).toBeInTheDocument()
  })
})
