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
  it('renders HomePage', () => {
    render(<App />)
    expect(screen.getByText('HomePage')).toBeInTheDocument()
  })
})
