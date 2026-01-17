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
  }

  const mockBoard = [
    { id: 'tile-1', position: 0, x: 0, y: 0 },
    { id: 'tile-2', position: 1, x: 1, y: 0 },
    { id: 'tile-3', position: 2, x: 2, y: 0 },
  ]

  it('renders player token on perimeter tile', () => {
    const { container } = render(
      <PlayerToken
        player={mockPlayer}
        position={0}
        boardSize={4}
        board={mockBoard}
      />
    )
    expect(container.querySelector('.player-token')).toBeInTheDocument()
  })

  it('returns null when tile not found', () => {
    const { container } = render(
      <PlayerToken
        player={mockPlayer}
        position={99}
        boardSize={4}
        board={mockBoard}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it('returns null when tile is not on perimeter', () => {
    const innerTileBoard = [
      { id: 'tile-1', position: 0, x: 1, y: 1 },
    ]
    const { container } = render(
      <PlayerToken
        player={mockPlayer}
        position={0}
        boardSize={4}
        board={innerTileBoard}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it('displays player initial', () => {
    const { container } = render(
      <PlayerToken
        player={mockPlayer}
        position={0}
        boardSize={4}
        board={mockBoard}
      />
    )
    expect(container.textContent).toContain('T')
  })

  it('handles tiles on different perimeter edges', () => {
    const boardEdges = [
      { id: 'tile-1', position: 0, x: 0, y: 0 },      // top-left
      { id: 'tile-2', position: 1, x: 3, y: 0 },      // top-right
      { id: 'tile-3', position: 2, x: 0, y: 3 },      // bottom-left
      { id: 'tile-4', position: 3, x: 3, y: 3 },      // bottom-right
    ]

    boardEdges.forEach((tile, index) => {
      const { container, unmount } = render(
        <PlayerToken
          player={mockPlayer}
          position={tile.position}
          boardSize={4}
          board={boardEdges}
        />
      )
      expect(container.querySelector('.player-token')).toBeInTheDocument()
      unmount()
    })
  })
})
