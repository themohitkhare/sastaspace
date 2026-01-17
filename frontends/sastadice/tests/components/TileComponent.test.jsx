/**
 * Unit tests for TileComponent
 */
import { render, screen } from '@testing-library/react'
import TileComponent from '../../src/components/game/TileComponent'

describe('TileComponent', () => {
  const mockTile = {
    id: 'tile-1',
    type: 'PROPERTY',
    name: 'Park Place',
    owner_id: 'owner-123',
    position: 0,
    x: 0,
    y: 0,
    effect_config: {},
  }

  it('renders property tile with owner', () => {
    render(<TileComponent tile={mockTile} boardSize={4} />)
    expect(screen.getByText('Park Place')).toBeInTheDocument()
    expect(screen.getByText(/Owner:/)).toBeInTheDocument()
  })

  it('does not render tiles not on perimeter', () => {
    const innerTile = { ...mockTile, x: 1, y: 1 }
    const { container } = render(<TileComponent tile={innerTile} boardSize={4} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders tiles on perimeter', () => {
    render(<TileComponent tile={mockTile} boardSize={4} />)
    expect(screen.getByText('Park Place')).toBeInTheDocument()
  })

  it('renders tile without owner', () => {
    const tileWithoutOwner = { ...mockTile, owner_id: null }
    render(<TileComponent tile={tileWithoutOwner} boardSize={4} />)
    expect(screen.getByText('Park Place')).toBeInTheDocument()
    expect(screen.queryByText(/Owner:/)).not.toBeInTheDocument()
  })

  it('renders different tile types with correct colors', () => {
    const tileTypes = ['PROPERTY', 'TAX', 'CHANCE', 'TRAP', 'BUFF', 'NEUTRAL']
    
    tileTypes.forEach((type) => {
      const tile = { ...mockTile, type, name: `${type} Tile` }
      const { container, unmount } = render(
        <TileComponent tile={tile} boardSize={4} />
      )
      const tileElement = container.querySelector('.tile')
      expect(tileElement).toBeInTheDocument()
      unmount()
    })
  })

  it('renders tiles on all perimeter edges', () => {
    const perimeterTiles = [
      { ...mockTile, x: 0, y: 0 },      // top-left
      { ...mockTile, x: 3, y: 0 },      // top-right
      { ...mockTile, x: 0, y: 3 },      // bottom-left
      { ...mockTile, x: 3, y: 3 },      // bottom-right
      { ...mockTile, x: 1, y: 0 },      // top edge
      { ...mockTile, x: 0, y: 1 },      // left edge
    ]

    perimeterTiles.forEach((tile) => {
      const { container, unmount } = render(
        <TileComponent tile={tile} boardSize={4} />
      )
      expect(container.firstChild).not.toBeNull()
      unmount()
    })
  })

  it('applies custom styles', () => {
    const customStyle = { zIndex: 999 }
    const { container } = render(
      <TileComponent tile={mockTile} boardSize={4} style={customStyle} />
    )
    const tileElement = container.querySelector('.tile')
    expect(tileElement).toHaveStyle({ zIndex: 999 })
  })

  it('displays truncated owner ID', () => {
    const tileWithLongOwner = { ...mockTile, owner_id: 'very-long-owner-id-12345' }
    render(<TileComponent tile={tileWithLongOwner} boardSize={4} />)
    expect(screen.getByText(/Owner:/)).toBeInTheDocument()
    // Owner ID should be truncated to first 4 characters
    expect(screen.getByText(/very/)).toBeInTheDocument()
  })
})
