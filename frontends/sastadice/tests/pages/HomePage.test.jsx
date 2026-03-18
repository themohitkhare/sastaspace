/**
 * Tests for HomePage component
 */
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import HomePage from '../../src/pages/HomePage'
import { useGameStore } from '../../src/store/useGameStore'

vi.mock('../../src/store/useGameStore')

const renderWithRouter = (component) => {
  return render(<MemoryRouter initialEntries={['/']}>{component}</MemoryRouter>)
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
    expect(screen.getByPlaceholderText('PASTE OR TYPE CODE...')).toBeInTheDocument()
  })

  it('keeps CPU selection behind Advanced by default', async () => {
    renderWithRouter(<HomePage />)

    expect(screen.queryByText('SELECT CPU OPPONENTS:')).not.toBeInTheDocument()

    const user = userEvent.setup()
    await act(async () => {
      await user.click(screen.getByRole('button', { name: /advanced: add cpu opponents/i }))
    })

    expect(screen.getByText('SELECT CPU OPPONENTS:')).toBeInTheDocument()
  })
})
