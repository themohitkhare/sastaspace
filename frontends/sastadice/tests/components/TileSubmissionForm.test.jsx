/**
 * Tests for TileSubmissionForm component
 */
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, beforeEach } from 'vitest'
import TileSubmissionForm from '../../src/components/lobby/TileSubmissionForm'

describe('TileSubmissionForm', () => {
  let setTiles
  let tiles

  beforeEach(() => {
    setTiles = vi.fn()
    tiles = []
  })

  it('renders 5 tile input slots', () => {
    render(<TileSubmissionForm tiles={tiles} setTiles={setTiles} />)
    expect(screen.getByText('SUBMIT 5 TILES (0/5)')).toBeInTheDocument()
    const inputs = screen.getAllByPlaceholderText(/Tile \d+ name/)
    expect(inputs).toHaveLength(5)
  })

  it('displays current tile count', () => {
    tiles = [
      { type: 'PROPERTY', name: 'Tile 1', effect_config: {} },
      { type: 'TAX', name: 'Tile 2', effect_config: {} },
    ]
    render(<TileSubmissionForm tiles={tiles} setTiles={setTiles} />)
    expect(screen.getByText('SUBMIT 5 TILES (2/5)')).toBeInTheDocument()
  })

  it('updates tile name when input changes', async () => {
    const user = userEvent.setup()
    render(<TileSubmissionForm tiles={tiles} setTiles={setTiles} />)
    
    const input = screen.getByPlaceholderText('Tile 1 name')
    await user.type(input, 'Test Tile')

    expect(setTiles).toHaveBeenCalled()
  })

  it('updates tile type when select changes', async () => {
    const user = userEvent.setup()
    render(<TileSubmissionForm tiles={tiles} setTiles={setTiles} />)
    
    const selects = screen.getAllByRole('combobox')
    await user.selectOptions(selects[0], 'TAX')

    expect(setTiles).toHaveBeenCalled()
  })

  it('has all tile types in select options', () => {
    render(<TileSubmissionForm tiles={tiles} setTiles={setTiles} />)
    const selects = screen.getAllByRole('combobox')
    const firstSelect = selects[0]
    
    const options = Array.from(firstSelect.options).map(opt => opt.value)
    expect(options).toEqual(['PROPERTY', 'TAX', 'CHANCE', 'TRAP', 'BUFF'])
  })

  it('initializes empty tiles with PROPERTY type', async () => {
    const user = userEvent.setup()
    render(<TileSubmissionForm tiles={tiles} setTiles={setTiles} />)
    
    const input = screen.getByPlaceholderText('Tile 1 name')
    await user.type(input, 'Test')

    const call = setTiles.mock.calls[0][0]
    expect(call[0].type).toBe('PROPERTY')
  })

  it('handles partial tile updates', async () => {
    tiles = [
      { type: 'PROPERTY', name: 'Tile 1', effect_config: {} },
    ]
    const user = userEvent.setup()
    render(<TileSubmissionForm tiles={tiles} setTiles={setTiles} />)
    
    const input = screen.getByPlaceholderText('Tile 2 name')
    await user.type(input, 'New Tile')

    expect(setTiles).toHaveBeenCalled()
  })
})
