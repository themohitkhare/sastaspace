/**
 * Tests for HomePage component
 */
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { vi } from 'vitest'
import HomePage from '../../src/pages/HomePage'
import { useGameStore } from '../../src/store/useGameStore'

vi.mock('../../src/store/useGameStore')

const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('HomePage', () => {
  beforeEach(() => {
    useGameStore.mockImplementation((selector) => {
      const state = {
        setGameId: vi.fn(),
        setGame: vi.fn(),
        reset: vi.fn(),
      }
      return selector(state)
    })
  })

  it('renders heading', () => {
    renderWithRouter(<HomePage />)
    expect(screen.getByText('SASTADICE')).toBeInTheDocument()
  })

  it('renders tagline', () => {
    renderWithRouter(<HomePage />)
    expect(screen.getByText('ROLL THE DICE. BUILD THE BOARD. EMBRACE THE CHAOS.')).toBeInTheDocument()
  })

  it('renders create game button', () => {
    renderWithRouter(<HomePage />)
    expect(screen.getByText(/CREATE GAME/)).toBeInTheDocument()
  })

  it('renders join game input', () => {
    renderWithRouter(<HomePage />)
    expect(screen.getByPlaceholderText('ENTER CODE...')).toBeInTheDocument()
  })
})
