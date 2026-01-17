/**
 * Tests for HomePage component
 */
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import HomePage from '../../src/pages/HomePage'

const renderWithRouter = (component) => {
  return render(<BrowserRouter>{component}</BrowserRouter>)
}

describe('HomePage', () => {
  it('renders heading', () => {
    renderWithRouter(<HomePage />)
    expect(screen.getByText('SASTADICE')).toBeInTheDocument()
  })

  it('renders tagline', () => {
    renderWithRouter(<HomePage />)
    expect(screen.getByText('Roll the dice, embrace the chaos.')).toBeInTheDocument()
  })
})
