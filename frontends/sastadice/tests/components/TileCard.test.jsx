import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import TileCard from '../../src/components/game/TileCard'

describe('TileCard', () => {
  it('renders NODE tile with server icon', () => {
    const tile = { id: '1', type: 'NODE', name: 'Server Node', position: 5, price: 200, rent: 50 }
    render(<TileCard tile={tile} isVisible={true} />)
    expect(screen.getByText('🖥️')).toBeDefined()
  })

  it('renders MARKET tile with shop icon', () => {
    const tile = { id: '2', type: 'MARKET', name: 'Black Market', position: 18 }
    render(<TileCard tile={tile} isVisible={true} />)
    expect(screen.getByText('🏪')).toBeDefined()
  })

  it('renders TELEPORT tile with portal icon', () => {
    const tile = { id: '3', type: 'TELEPORT', name: 'The Glitch', position: 6 }
    render(<TileCard tile={tile} isVisible={true} />)
    expect(screen.getByText('🌀')).toBeDefined()
  })

  it('renders GO_TO_JAIL tile with siren icon', () => {
    const tile = { id: '4', type: 'GO_TO_JAIL', name: '404: Access Denied', position: 24 }
    render(<TileCard tile={tile} isVisible={true} />)
    expect(screen.getByText('🚨')).toBeDefined()
  })

  it('renders JAIL tile with lock icon', () => {
    const tile = { id: '5', type: 'JAIL', name: 'Server Downtime', position: 12 }
    render(<TileCard tile={tile} isVisible={true} />)
    expect(screen.getByText('🔒')).toBeDefined()
  })

  it('returns null when not visible', () => {
    const tile = { id: '1', type: 'PROPERTY', name: 'Test', position: 1 }
    const { container } = render(<TileCard tile={tile} isVisible={false} />)
    expect(container.innerHTML).toBe('')
  })
})
