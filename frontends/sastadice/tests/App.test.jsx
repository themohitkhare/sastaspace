/**
 * Tests for App component
 */
import { render, screen } from '@testing-library/react'
import App from '../src/App'
import HomePage from '../src/pages/HomePage'

vi.mock('../src/pages/HomePage', () => ({
  default: () => <div>HomePage</div>,
}))

describe('App', () => {
  it('renders app header and HomePage', () => {
    window.history.pushState({}, 'Test page', '/sastadice/')
    render(<App />)

    const hubLink = screen.getByRole('link', { name: /sastaspace/i })
    expect(hubLink).toHaveAttribute('href', '/')
    expect(hubLink).toHaveClass('focus-visible:ring-2')

    expect(screen.getByText('SASTADICE')).toBeInTheDocument()
    expect(screen.getByText('HomePage')).toBeInTheDocument()
  })
})
