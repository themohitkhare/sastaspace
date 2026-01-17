import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import KeyStatus from '../../src/components/lobby/KeyStatus'

const mockPlayer = {
  id: 'p1',
  name: 'Alice',
  ready: false,
  color: '#FF0000',
}

describe('KeyStatus', () => {
  it('renders player name', () => {
    render(<KeyStatus player={mockPlayer} />)
    expect(screen.getByText('ALICE')).toBeInTheDocument()
  })

  it('shows standing by when not ready', () => {
    render(<KeyStatus player={mockPlayer} />)
    expect(screen.getByText('STANDING BY')).toBeInTheDocument()
  })

  it('shows key armed when ready', () => {
    const readyPlayer = { ...mockPlayer, ready: true }
    render(<KeyStatus player={readyPlayer} />)
    expect(screen.getByText('✓ KEY ARMED')).toBeInTheDocument()
  })

  it('shows YOU badge when isMe', () => {
    render(<KeyStatus player={mockPlayer} isMe={true} />)
    expect(screen.getByText('YOU')).toBeInTheDocument()
  })

  it('shows HOST badge when isHost', () => {
    render(<KeyStatus player={mockPlayer} isHost={true} />)
    expect(screen.getByText('HOST')).toBeInTheDocument()
  })

  it('shows kick button when canKick and not isMe', () => {
    const onKick = vi.fn()
    render(
      <KeyStatus 
        player={mockPlayer} 
        canKick={true} 
        isMe={false}
        onKick={onKick}
      />
    )
    const kickButton = screen.getByRole('button')
    expect(kickButton).toBeInTheDocument()
    fireEvent.click(kickButton)
    expect(onKick).toHaveBeenCalledWith('p1')
  })

  it('does not show kick button when isMe', () => {
    render(
      <KeyStatus 
        player={mockPlayer} 
        canKick={true} 
        isMe={true}
      />
    )
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('uses default color when player color not provided', () => {
    const playerNoColor = { ...mockPlayer, color: undefined }
    const { container } = render(<KeyStatus player={playerNoColor} />)
    expect(container.firstChild).toBeInTheDocument()
  })

  it('applies ready styles when player is ready', () => {
    const readyPlayer = { ...mockPlayer, ready: true }
    const { container } = render(<KeyStatus player={readyPlayer} />)
    expect(container.querySelector('.border-green-500')).toBeInTheDocument()
  })

  it('applies ring styles when isMe', () => {
    const { container } = render(<KeyStatus player={mockPlayer} isMe={true} />)
    expect(container.querySelector('.ring-2')).toBeInTheDocument()
  })
})
