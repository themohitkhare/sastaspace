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
})
