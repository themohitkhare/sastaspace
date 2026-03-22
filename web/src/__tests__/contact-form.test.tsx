import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { ContactForm } from '@/components/result/contact-form'

// Mock motion/react to avoid animation complexity in tests
vi.mock('motion/react', () => ({
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  motion: {
    div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
      <div {...props}>{children}</div>
    ),
  },
}))

// Mock lucide-react
vi.mock('lucide-react', () => ({
  Loader2: () => <svg data-testid="loader-icon" />,
}))

// Mock Turnstile
vi.mock('@marsidev/react-turnstile', () => ({
  Turnstile: () => null,
}))

beforeEach(() => {
  vi.restoreAllMocks()
  // Disable Turnstile by default in tests
  vi.stubEnv('NEXT_PUBLIC_ENABLE_TURNSTILE', 'false')
})

/** Fill in contact form fields and click submit. */
function fillAndSubmit(
  fields: { name?: string; email?: string; message?: string } = {}
) {
  const { name = 'John', email = 'john@example.com', message = 'Hello' } = fields
  if (name) fireEvent.change(screen.getByLabelText('Name'), { target: { value: name } })
  if (email) fireEvent.change(screen.getByLabelText('Email'), { target: { value: email } })
  if (message) fireEvent.change(screen.getByLabelText('Message'), { target: { value: message } })
  fireEvent.click(screen.getByRole('button', { name: /send message/i }))
}

describe('ContactForm', () => {
  it('renders the form fields', () => {
    render(<ContactForm subdomain="example-com" />)

    expect(screen.getByLabelText('Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Email')).toBeInTheDocument()
    expect(screen.getByLabelText('Message')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send message/i })).toBeInTheDocument()
  })

  it('shows validation errors when submitting empty form', () => {
    render(<ContactForm subdomain="example-com" />)

    fireEvent.click(screen.getByRole('button', { name: /send message/i }))

    expect(screen.getByText('Please enter your name')).toBeInTheDocument()
    expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument()
    expect(screen.getByText('Please enter a message')).toBeInTheDocument()
  })

  it('shows email validation error for invalid email', () => {
    render(<ContactForm subdomain="example-com" />)

    fillAndSubmit({ email: 'not-an-email' })

    expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument()
    expect(screen.queryByText('Please enter your name')).not.toBeInTheDocument()
  })

  it('submits form successfully and shows thank you message', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      json: async () => ({ ok: true }),
    } as Response)

    render(<ContactForm subdomain="example-com" />)

    fillAndSubmit({ message: 'Hello there' })

    await waitFor(() => {
      expect(screen.getByText(/thanks/i)).toBeInTheDocument()
    })
  })

  it('shows server error on failed submission', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      json: async () => ({ ok: false, error: 'Failed to send message' }),
    } as Response)

    render(<ContactForm subdomain="example-com" />)

    fillAndSubmit()

    await waitFor(() => {
      expect(screen.getByText('Failed to send message')).toBeInTheDocument()
    })
  })

  it('shows generic error on network failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    render(<ContactForm subdomain="example-com" />)

    fillAndSubmit()

    await waitFor(() => {
      expect(screen.getByText('Something went wrong. Please try again.')).toBeInTheDocument()
    })
  })

  it('sends correct payload including subdomain', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      json: async () => ({ ok: true }),
    } as Response)

    render(<ContactForm subdomain="my-site-com" />)

    fillAndSubmit({ name: 'Jane', email: 'jane@test.com', message: 'Hi' })

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: 'Jane',
          email: 'jane@test.com',
          message: 'Hi',
          website: '',
          turnstileToken: null,
          subdomain: 'my-site-com',
        }),
      })
    })
  })

  it('clears field-level error when user types in that field', () => {
    render(<ContactForm subdomain="example-com" />)

    // Submit empty to get all errors
    fireEvent.click(screen.getByRole('button', { name: /send message/i }))
    expect(screen.getByText('Please enter your name')).toBeInTheDocument()

    // Type in name field — name error should clear, others remain
    fireEvent.change(screen.getByLabelText('Name'), { target: { value: 'J' } })
    expect(screen.queryByText('Please enter your name')).not.toBeInTheDocument()
    expect(screen.getByText('Please enter a valid email address')).toBeInTheDocument()
  })
})
