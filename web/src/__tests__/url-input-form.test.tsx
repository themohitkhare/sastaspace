import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { UrlInputForm } from '@/components/landing/url-input-form'

// Mock lucide-react to avoid SVG rendering issues in jsdom
vi.mock('lucide-react', () => ({
  Globe: () => <svg data-testid="globe-icon" />,
}))

describe('UrlInputForm', () => {
  it('renders the input and submit button', () => {
    render(<UrlInputForm onSubmit={() => {}} />)

    expect(screen.getByPlaceholderText('yourwebsite.com')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /redesign my site/i })).toBeInTheDocument()
  })

  it('shows error when submitting empty input', () => {
    const onSubmit = vi.fn()
    render(<UrlInputForm onSubmit={onSubmit} />)

    fireEvent.click(screen.getByRole('button', { name: /redesign my site/i }))

    expect(screen.getByText('Please enter a valid website address')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('shows error for invalid URL', () => {
    const onSubmit = vi.fn()
    render(<UrlInputForm onSubmit={onSubmit} />)

    fireEvent.change(screen.getByPlaceholderText('yourwebsite.com'), {
      target: { value: 'notaurl' },
    })
    fireEvent.click(screen.getByRole('button', { name: /redesign my site/i }))

    expect(screen.getByText('Please enter a valid website address')).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('calls onSubmit with validated URL for valid input', () => {
    const onSubmit = vi.fn()
    render(<UrlInputForm onSubmit={onSubmit} />)

    fireEvent.change(screen.getByPlaceholderText('yourwebsite.com'), {
      target: { value: 'example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: /redesign my site/i }))

    expect(onSubmit).toHaveBeenCalledWith('https://example.com/')
  })

  it('clears error when user types after validation failure', () => {
    render(<UrlInputForm onSubmit={() => {}} />)

    // Submit empty to trigger error
    fireEvent.click(screen.getByRole('button', { name: /redesign my site/i }))
    expect(screen.getByText('Please enter a valid website address')).toBeInTheDocument()

    // Type something — error should clear
    fireEvent.change(screen.getByPlaceholderText('yourwebsite.com'), {
      target: { value: 'e' },
    })
    expect(screen.queryByText('Please enter a valid website address')).not.toBeInTheDocument()
  })

  it('has accessible label for the input', () => {
    render(<UrlInputForm onSubmit={() => {}} />)

    expect(screen.getByLabelText('Website URL')).toBeInTheDocument()
  })

  it('sets aria-invalid on the input when there is an error', () => {
    render(<UrlInputForm onSubmit={() => {}} />)

    fireEvent.click(screen.getByRole('button', { name: /redesign my site/i }))

    const input = screen.getByPlaceholderText('yourwebsite.com')
    expect(input).toHaveAttribute('aria-invalid', 'true')
  })
})
