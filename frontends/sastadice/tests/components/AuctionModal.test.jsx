import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import AuctionModal from '../../src/components/game/AuctionModal'

describe('AuctionModal', () => {
    const mockOnBid = vi.fn()
    const mockOnExpire = vi.fn()

    const mockAuctionState = {
        property_id: 'tile_1',
        highest_bid: 500,
        highest_bidder_id: 'p2',
        min_bid_increment: 10,
        end_time: Date.now() / 1000 + 30 // 30s remaining
    }

    const mockTiles = [
        { id: 'tile_1', name: 'Boardwalk', price: 400, color: 'blue' }
    ]

    const mockPlayers = [
        { id: 'p1', name: 'Player 1' },
        { id: 'p2', name: 'Player 2' }
    ]

    it('renders correctly', () => {
        render(
            <AuctionModal
                auctionState={mockAuctionState}
                tiles={mockTiles}
                players={mockPlayers}
                playerId="p1"
                onBid={mockOnBid}
                onExpire={mockOnExpire}
            />
        )

        expect(screen.getByText('⚠️ BIDDING WAR ⚠️')).toBeInTheDocument()
        // Use regex for case insensitivity or partial match
        expect(screen.getByText(/CURRENT PRICE/i)).toBeInTheDocument()
        expect(screen.getByText('$500')).toBeInTheDocument()
        expect(screen.getByText('Boardwalk')).toBeInTheDocument()
    })

    it('calculates bid buttons correctly', () => {
        render(
            <AuctionModal
                auctionState={mockAuctionState}
                tiles={mockTiles}
                players={mockPlayers}
                playerId="p1"
                onBid={mockOnBid}
                onExpire={mockOnExpire}
            />
        )

        // Current bid 500. Buttons should be +10, +50, +100
        // Resulting bids: 510, 550, 600

        const bid510 = screen.getByText('BID $510')
        const bid550 = screen.getByText('BID $550')
        const bid600 = screen.getByText('BID $600')

        expect(bid510).toBeInTheDocument()
        expect(bid550).toBeInTheDocument()
        expect(bid600).toBeInTheDocument()

        // Test click
        fireEvent.click(bid550)
        expect(mockOnBid).toHaveBeenCalledWith(550)
    })

    it('disables buttons if player is highest bidder', () => {
        // Player 2 is highest bidder in mock state
        render(
            <AuctionModal
                auctionState={mockAuctionState}
                tiles={mockTiles}
                players={mockPlayers}
                playerId="p2" // I am p2
                onBid={mockOnBid}
                onExpire={mockOnExpire}
            />
        )

        const button = screen.getByText('BID $510').closest('button')
        expect(button).toBeDisabled()
        expect(screen.getByText(/YOU ARE WINNING/i)).toBeInTheDocument()
    })

    it('shows panic mode visuals when time is low', () => {
        const panicState = {
            ...mockAuctionState,
            end_time: Date.now() / 1000 + 3
        }

        render(
            <AuctionModal
                auctionState={panicState}
                tiles={mockTiles}
                players={mockPlayers}
                playerId="p1"
                onBid={mockOnBid}
                onExpire={mockOnExpire}
            />
        )

        // Find the inner card div which has the border styling.
        // The "⚠️ BIDDING WAR ⚠️" header is inside a div, which is inside *another* div that has the border.
        // Hierarchy:
        // Outer (fixed inset-0)
        //   Inner (max-w-md ... border-red-600)
        //     Header Div ("⚠️ BIDDING WAR ⚠️")

        const header = screen.getByText('⚠️ BIDDING WAR ⚠️')
        // header is h2
        // header.parent is div (text-center)
        // header.parent.parent is div (border-red-600...)

        const modalContent = header.closest('div').parentElement

        expect(modalContent).toHaveClass('border-red-600')
        expect(modalContent).toHaveClass('animate-pulse')
    })
})
