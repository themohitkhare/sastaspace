/**
 * Tests for VictoryScreen component
 */
import { render, screen, fireEvent } from '@testing-library/react'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import VictoryScreen from '../../src/components/game/VictoryScreen'
import { useGameStore } from '../../src/store/useGameStore'

vi.mock('../../src/store/useGameStore')
vi.mock('react-confetti', () => ({
    default: () => <div data-testid="confetti">Confetti</div>,
}))

const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
    const actual = await vi.importActual('react-router-dom')
    return {
        ...actual,
        useNavigate: () => mockNavigate,
    }
})

const renderWithRouter = (component) => {
    return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('VictoryScreen', () => {
    const mockGame = {
        id: 'game-123',
        status: 'FINISHED',
        players: [
            { id: 'player-1', name: 'Alice', cash: 5000, color: '#FF6B6B', is_bankrupt: false },
            { id: 'player-2', name: 'Bob', cash: 2000, color: '#4ECDC4', is_bankrupt: false },
            { id: 'player-3', name: 'Charlie', cash: 0, color: '#FFE66D', is_bankrupt: true },
        ],
        board: [],
    }

    const mockWinner = mockGame.players[0] // Alice

    beforeEach(() => {
        vi.clearAllMocks()
        useGameStore.mockImplementation((selector) => {
            const state = {
                reset: vi.fn(),
            }
            return selector(state)
        })
    })

    it('renders winner name prominently', () => {
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} />)
        expect(screen.getByText('Alice')).toBeInTheDocument()
    })

    it('displays VICTORY text', () => {
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} />)
        expect(screen.getByText('VICTORY')).toBeInTheDocument()
    })

    it('displays winner cash amount', () => {
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} />)
        expect(screen.getByText('$5,000')).toBeInTheDocument()
    })

    it('renders confetti component', () => {
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} />)
        expect(screen.getByTestId('confetti')).toBeInTheDocument()
    })

    it('renders BANKRUPT PLAYERS toggle button', () => {
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} />)
        expect(screen.getByText(/BANKRUPT PLAYERS/)).toBeInTheDocument()
    })

    it('shows stats when BANKRUPT PLAYERS is clicked', () => {
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} />)

        // Stats should be hidden initially (or not found in the dom)
        expect(screen.queryByText('#2')).not.toBeInTheDocument()

        // Click toggle
        fireEvent.click(screen.getByText(/BANKRUPT PLAYERS/))

        // Stats should now be visible (Bob is #2)
        expect(screen.getByText('#2')).toBeInTheDocument()
        expect(screen.getByText('Bob')).toBeInTheDocument()
    })

    it('shows ELIMINATED indicator for bankrupt players', () => {
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} />)

        // Expand details
        fireEvent.click(screen.getByText(/BANKRUPT PLAYERS/))

        // Charlie is bankrupt
        expect(screen.getByText('ELIMINATED')).toBeInTheDocument()
    })

    it('renders PLAY AGAIN button', () => {
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} />)
        expect(screen.getByText('PLAY AGAIN')).toBeInTheDocument()
    })

    it('renders RETURN TO HOME button', () => {
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} />)
        expect(screen.getByText('RETURN TO HOME')).toBeInTheDocument()
    })

    it('calls onPlayAgain when PLAY AGAIN is clicked', () => {
        const mockReset = vi.fn()
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} onPlayAgain={mockReset} />)

        fireEvent.click(screen.getByText('PLAY AGAIN'))
        expect(mockReset).toHaveBeenCalled()
    })

    it('navigates to / when RETURN TO HOME is clicked', () => {
        renderWithRouter(<VictoryScreen game={mockGame} winner={mockWinner.id} players={mockGame.players} />)

        fireEvent.click(screen.getByText('RETURN TO HOME'))

        expect(mockNavigate).toHaveBeenCalledWith('/')
    })
})
