/**
 * Unit tests for TileComponent
 */
import { render, screen } from '@testing-library/react'
import TileComponent from '../../src/components/game/TileComponent'

describe('TileComponent', () => {
  const mockPlayers = [
    { id: 'owner-123', name: 'Alice', color: '#FF6B6B' },
    { id: 'owner-456', name: 'Bob', color: '#4ECDC4' },
  ]

  const mockTile = {
    id: 'tile-1',
    type: 'PROPERTY',
    name: 'Park Place',
    owner_id: 'owner-123',
    position: 0,
    x: 0,
    y: 0,
    price: 200,
    rent: 50,
    effect_config: {},
  }

  it('renders property tile with name (uppercase)', () => {
    render(<TileComponent tile={mockTile} players={mockPlayers} />)
    expect(screen.getByText('PARK PLACE')).toBeInTheDocument()
  })

  it('renders tile type badge', () => {
    render(<TileComponent tile={mockTile} players={mockPlayers} />)
    expect(screen.getByText('PROPERTY')).toBeInTheDocument()
  })

  it('renders owner name badge when tile has owner', () => {
    render(<TileComponent tile={mockTile} players={mockPlayers} />)
    // Owner badge shows truncated owner name (first 6 chars)
    expect(screen.getByText('ALICE')).toBeInTheDocument()
  })

  it('renders price for unowned property', () => {
    const unownedTile = { ...mockTile, owner_id: null }
    render(<TileComponent tile={unownedTile} players={mockPlayers} />)
    expect(screen.getByText('$200')).toBeInTheDocument()
  })

  it('renders rent for owned property', () => {
    render(<TileComponent tile={mockTile} players={mockPlayers} />)
    expect(screen.getByText('RENT: $50')).toBeInTheDocument()
  })

  it('renders different tile types', () => {
    const tileTypes = ['PROPERTY', 'TAX', 'CHANCE', 'TRAP', 'BUFF', 'NEUTRAL', 'GO']

    tileTypes.forEach((type) => {
      const tile = { ...mockTile, type, name: `${type} Tile` }
      const { container, unmount } = render(
        <TileComponent tile={tile} players={mockPlayers} />
      )
      const tileElement = container.querySelector('.tile')
      expect(tileElement).toBeInTheDocument()
      unmount()
    })
  })

  it('renders SASTA badge for CHANCE tiles', () => {
    const chanceTile = { ...mockTile, type: 'CHANCE' }
    render(<TileComponent tile={chanceTile} players={mockPlayers} />)
    expect(screen.getByText('SASTA')).toBeInTheDocument()
  })

  it('renders GO tile with GO indicator', () => {
    const goTile = { ...mockTile, type: 'GO', name: 'GO' }
    render(<TileComponent tile={goTile} players={mockPlayers} />)
    expect(screen.getByText(/>> GO >>/)).toBeInTheDocument()
  })

  it('applies dashed border for unowned tiles', () => {
    const unownedTile = { ...mockTile, owner_id: null }
    const { container } = render(
      <TileComponent tile={unownedTile} players={mockPlayers} />
    )
    const tileElement = container.querySelector('.tile')
    expect(tileElement).toHaveStyle({ borderStyle: 'dashed' })
  })

  it('applies solid border for owned tiles', () => {
    const { container } = render(
      <TileComponent tile={mockTile} players={mockPlayers} />
    )
    const tileElement = container.querySelector('.tile')
    expect(tileElement).toHaveStyle({ borderStyle: 'solid' })
  })

  it('distinguishes owned vs unowned tiles visually', () => {
    const unownedTile = { ...mockTile, owner_id: null }
    const { container } = render(
      <TileComponent tile={unownedTile} players={mockPlayers} />
    )
    const tileElement = container.querySelector('.tile')
    // Unowned tiles have dashed borders (tested above)
    expect(tileElement).toHaveStyle({ borderStyle: 'dashed' })
  })

  it('applies custom styles', () => {
    const customStyle = { zIndex: 999 }
    const { container } = render(
      <TileComponent tile={mockTile} players={mockPlayers} style={customStyle} />
    )
    const tileElement = container.querySelector('.tile')
    expect(tileElement).toHaveStyle({ zIndex: 999 })
  })
})
