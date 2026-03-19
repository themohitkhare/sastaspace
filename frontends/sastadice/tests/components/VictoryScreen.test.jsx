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
        current_round: 15,
        players: [
            { id: 'player-1', name: 'Alice', cash: 5000, color: '#FF6B6B', is_bankrupt: false, properties: [] },
            { id: 'player-2', name: 'Bob', cash: 2000, color: '#4ECDC4', is_bankrupt: false, properties: [] },
            { id: 'player-3', name: 'Charlie', cash: 0, color: '#FFE66D', is_bankrupt: true, properties: [] },
        ],
        board: [
            { id: 'tile-1', name: 'Prop A', type: 'PROPERTY', owner_id: 'player-1', price: 200 },
            { id: 'tile-2', name: 'Prop B', type: 'PROPERTY', owner_id: 'player-1', price: 300 },
            { id: 'tile-3', name: 'Prop C', type: 'PROPERTY', owner_id: 'player-2', price: 150 },
        ],
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
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)
        expect(screen.getByText('Alice')).toBeInTheDocument()
    })

    it('displays VICTORY text', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)
        expect(screen.getByText('VICTORY')).toBeInTheDocument()
    })

    it('displays winner cash amount', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)
        expect(screen.getByText('$5,000')).toBeInTheDocument()
    })

    it('renders confetti component', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)
        expect(screen.getByTestId('confetti')).toBeInTheDocument()
    })

    it('renders BANKRUPT PLAYERS toggle button', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)
        expect(screen.getByText(/BANKRUPT PLAYERS/)).toBeInTheDocument()
    })

    it('shows stats when BANKRUPT PLAYERS is clicked', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)

        // Stats should be hidden initially (or not found in the dom)
        expect(screen.queryByText('#2')).not.toBeInTheDocument()

        // Click toggle
        fireEvent.click(screen.getByText(/BANKRUPT PLAYERS/))

        // Stats should now be visible (Bob is #2)
        expect(screen.getByText('#2')).toBeInTheDocument()
        expect(screen.getByText('Bob')).toBeInTheDocument()
    })

    it('shows ELIMINATED indicator for bankrupt players', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)

        // Expand details
        fireEvent.click(screen.getByText(/BANKRUPT PLAYERS/))

        // Charlie is bankrupt
        expect(screen.getByText('ELIMINATED')).toBeInTheDocument()
    })

    it('renders PLAY AGAIN button', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)
        expect(screen.getByText('PLAY AGAIN')).toBeInTheDocument()
    })

    it('renders RETURN TO HOME button', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)
        expect(screen.getByText('RETURN TO HOME')).toBeInTheDocument()
    })

    it('calls onPlayAgain when PLAY AGAIN is clicked', () => {
        const mockReset = vi.fn()
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} onPlayAgain={mockReset} />)

        fireEvent.click(screen.getByText('PLAY AGAIN'))
        expect(mockReset).toHaveBeenCalled()
    })

    it('navigates to / when RETURN TO HOME is clicked', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)

        fireEvent.click(screen.getByText('RETURN TO HOME'))

        expect(mockNavigate).toHaveBeenCalledWith('/')
    })

    it('renders GAME STATS toggle button', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)
        expect(screen.getByText('GAME STATS')).toBeInTheDocument()
    })

    it('shows game stats when GAME STATS is clicked', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)

        fireEvent.click(screen.getByText('GAME STATS'))

        expect(screen.getByText('TURNS PLAYED')).toBeInTheDocument()
        expect(screen.getByText('15')).toBeInTheDocument()
        expect(screen.getByText('WINNER NET WORTH')).toBeInTheDocument()
    })

    it('shows property count per player in game stats', () => {
        renderWithRouter(<VictoryScreen winner={mockWinner.id} players={mockGame.players} game={mockGame} />)

        fireEvent.click(screen.getByText('GAME STATS'))

        expect(screen.getByText('2 PROPS')).toBeInTheDocument()
        expect(screen.getByText('1 PROPS')).toBeInTheDocument()
        expect(screen.getByText('0 PROPS')).toBeInTheDocument()
    })
})
