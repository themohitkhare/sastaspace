import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import LaunchKey from '../../src/components/lobby/LaunchKey'

describe('LaunchKey', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders with default state (not ready)', () => {
    render(<LaunchKey isReady={false} onToggle={() => {}} />)
    expect(screen.getByText('TURN TO ARM')).toBeInTheDocument()
    expect(screen.getByText('CLICK TO TURN KEY')).toBeInTheDocument()
  })

  it('shows armed state when ready', () => {
    render(<LaunchKey isReady={true} onToggle={() => {}} />)
    expect(screen.getByText('✓ ARMED')).toBeInTheDocument()
    expect(screen.getByText('WAITING FOR OTHER OPERATORS')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    render(<LaunchKey isReady={false} isLoading={true} onToggle={() => {}} />)
    expect(screen.getByText('TURNING...')).toBeInTheDocument()
  })

  it('calls onToggle when clicked', async () => {
    const onToggle = vi.fn()
    render(<LaunchKey isReady={false} onToggle={onToggle} />)
    
    const button = screen.getByRole('button')
    fireEvent.click(button)
    
    expect(onToggle).toHaveBeenCalledTimes(1)
  })

  it('does not call onToggle when loading', () => {
    const onToggle = vi.fn()
    render(<LaunchKey isReady={false} isLoading={true} onToggle={onToggle} />)
    
    const button = screen.getByRole('button')
    fireEvent.click(button)
    
    expect(onToggle).not.toHaveBeenCalled()
  })

  it('displays player name', () => {
    render(<LaunchKey isReady={false} onToggle={() => {}} playerName="Alice" />)
    expect(screen.getByText('ALICE')).toBeInTheDocument()
  })

  it('displays operator label', () => {
    render(<LaunchKey isReady={false} onToggle={() => {}} />)
    expect(screen.getByText('OPERATOR')).toBeInTheDocument()
  })

  it('displays status label', () => {
    render(<LaunchKey isReady={false} onToggle={() => {}} />)
    expect(screen.getByText('STATUS')).toBeInTheDocument()
  })

  it('uses player color for key', () => {
    const { container } = render(
      <LaunchKey isReady={false} onToggle={() => {}} playerColor="#FF0000" />
    )
    expect(container.querySelector('button')).toBeInTheDocument()
  })

  it('has correct aria-label when not ready', () => {
    render(<LaunchKey isReady={false} onToggle={() => {}} />)
    expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Turn key to ready up')
  })

  it('has correct aria-label when ready', () => {
    render(<LaunchKey isReady={true} onToggle={() => {}} />)
    expect(screen.getByRole('button')).toHaveAttribute('aria-label', 'Key turned - Ready')
  })

  it('shows OFF and ARM position markers', () => {
    render(<LaunchKey isReady={false} onToggle={() => {}} />)
    expect(screen.getByText('OFF')).toBeInTheDocument()
    expect(screen.getByText('ARM')).toBeInTheDocument()
  })

  it('animation resets after timeout', async () => {
    const onToggle = vi.fn()
    render(<LaunchKey isReady={false} onToggle={onToggle} />)
    
    const button = screen.getByRole('button')
    fireEvent.click(button)
    
    await act(async () => {
      vi.advanceTimersByTime(700)
    })
    
    expect(onToggle).toHaveBeenCalledTimes(1)
  })

  it('handles undefined playerName', () => {
    render(<LaunchKey isReady={false} onToggle={() => {}} playerName={undefined} />)
    expect(screen.getByText('OPERATOR')).toBeInTheDocument()
  })

  it('uses default color when playerColor not provided', () => {
    const { container } = render(<LaunchKey isReady={false} onToggle={() => {}} />)
    expect(container.querySelector('button')).toBeInTheDocument()
  })

  it('handles invalid hex color gracefully', () => {
    const { container } = render(
      <LaunchKey isReady={false} onToggle={() => {}} playerColor="not-a-color" />
    )
    expect(container.querySelector('button')).toBeInTheDocument()
  })
})
