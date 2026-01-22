import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import EventToast from '../../src/components/game/EventToast'

describe('EventToast', () => {
    it('renders with correct icon for MARKET_CRASH', () => {
        render(<EventToast lastEventMessage="Market Crash: All rent halved for 1 round" />)
        
        expect(screen.getByText('📉')).toBeInTheDocument()
        expect(screen.getByText(/Market Crash/i)).toBeInTheDocument()
    })

    it('renders with correct icon for BULL_MARKET', () => {
        render(<EventToast lastEventMessage="Bull Market: All rent +50% for 1 round" />)
        
        expect(screen.getByText('📈')).toBeInTheDocument()
        expect(screen.getByText(/Bull Market/i)).toBeInTheDocument()
    })

    it('renders with correct icon for WHISTLEBLOWER', () => {
        render(<EventToast lastEventMessage="🔍 Whistleblower: Player2 has $750" />)
        
        expect(screen.getByText('🔍')).toBeInTheDocument()
        expect(screen.getByText(/Whistleblower/i)).toBeInTheDocument()
    })

    it('renders with correct icon for FORK_REPO', () => {
        render(<EventToast lastEventMessage="Fork Repo: Clone upgrade to your property" />)
        
        expect(screen.getByText('🍴')).toBeInTheDocument()
        expect(screen.getByText(/Fork Repo/i)).toBeInTheDocument()
    })

    it('renders with correct icon for HOSTILE_TAKEOVER', () => {
        render(<EventToast lastEventMessage="⚔️ Hostile Takeover! Bought Park Place for $600" />)
        
        expect(screen.getByText('⚔️')).toBeInTheDocument()
        expect(screen.getByText(/Hostile Takeover/i)).toBeInTheDocument()
    })

    it('renders with correct icon for OPEN_SOURCE', () => {
        render(<EventToast lastEventMessage="🔓 Open Source! Park Place is free to land on for 1 round(s)" />)
        
        expect(screen.getByText('🔓')).toBeInTheDocument()
        expect(screen.getByText(/Open Source/i)).toBeInTheDocument()
    })

    it('renders with correct icon for SYSTEM_RESTORE', () => {
        render(<EventToast lastEventMessage="System Restore: Return to previous position" />)
        
        expect(screen.getByText('⏪')).toBeInTheDocument()
        expect(screen.getByText(/System Restore/i)).toBeInTheDocument()
    })

    it('renders with correct icon for SYSTEM_UPDATE', () => {
        render(<EventToast lastEventMessage="System Update: All players skip next turn" />)
        
        expect(screen.getByText('🔄')).toBeInTheDocument()
        expect(screen.getByText(/System Update/i)).toBeInTheDocument()
    })

    it('parses event type correctly for new events', () => {
        const { rerender } = render(<EventToast lastEventMessage="Whistleblower test" />)
        expect(screen.getByText('🔍')).toBeInTheDocument()
        
        rerender(<EventToast lastEventMessage="Fork Repo test" />)
        expect(screen.getByText('🍴')).toBeInTheDocument()
        
        rerender(<EventToast lastEventMessage="Hostile Takeover test" />)
        expect(screen.getByText('⚔️')).toBeInTheDocument()
    })

    it('dismisses toast after timeout', async () => {
        const { container } = render(<EventToast lastEventMessage="Test message" />)
        
        const toast = container.querySelector('.event-toast-container')
        expect(toast).toBeInTheDocument()
        
        await waitFor(() => {
            expect(container.querySelector('.event-toast-container')).toBeNull()
        }, { timeout: 3000 })
    })

    it('handles null or undefined message gracefully', () => {
        const { container } = render(<EventToast lastEventMessage={null} />)
        expect(container.querySelector('.event-toast-container')).toBeNull()
    })

    it('uses DEFAULT type for unrecognized messages', () => {
        render(<EventToast lastEventMessage="Some random message" />)
        expect(screen.getByText('📢')).toBeInTheDocument()
    })
})
