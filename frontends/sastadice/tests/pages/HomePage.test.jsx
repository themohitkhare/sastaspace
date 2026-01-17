/**
 * Tests for HomePage component
 */
import { render, screen } from '@testing-library/react'
import HomePage from '../../src/pages/HomePage'

describe('HomePage', () => {
  it('renders heading', () => {
    render(<HomePage />)
    expect(screen.getByText('SASTADICE')).toBeInTheDocument()
  })

  it('renders tagline', () => {
    render(<HomePage />)
    expect(screen.getByText('Roll the dice, embrace the chaos.')).toBeInTheDocument()
  })
})
