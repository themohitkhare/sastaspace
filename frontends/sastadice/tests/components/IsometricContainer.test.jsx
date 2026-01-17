/**
 * Tests for IsometricContainer component
 */
import { render } from '@testing-library/react'
import IsometricContainer, { TILE_SIZE } from '../../src/components/game/IsometricContainer'

describe('IsometricContainer', () => {
  it('renders children', () => {
    const { container } = render(
      <IsometricContainer boardSize={4}>
        <div>Test Child</div>
      </IsometricContainer>
    )
    expect(container.textContent).toContain('Test Child')
  })

  it('applies isometric transform styles', () => {
    const { container } = render(
      <IsometricContainer boardSize={4}>
        <div>Test</div>
      </IsometricContainer>
    )
    const element = container.querySelector('.isometric-board')
    expect(element).toHaveStyle({
      transform: 'rotateX(60deg) rotateZ(-45deg)',
      transformStyle: 'preserve-3d',
    })
  })

  it('calculates size based on boardSize', () => {
    const boardSize = 6
    const { container } = render(
      <IsometricContainer boardSize={boardSize}>
        <div>Test</div>
      </IsometricContainer>
    )
    const element = container.querySelector('.isometric-board')
    expect(element).toHaveStyle({
      width: `${boardSize * TILE_SIZE}px`,
      height: `${boardSize * TILE_SIZE}px`,
    })
  })

  it('exports TILE_SIZE constant', () => {
    expect(TILE_SIZE).toBe(100)
  })

  it('handles different board sizes', () => {
    const sizes = [4, 6, 8, 10]
    sizes.forEach((size) => {
      const { container, unmount } = render(
        <IsometricContainer boardSize={size}>
          <div>Test</div>
        </IsometricContainer>
      )
      const element = container.querySelector('.isometric-board')
      expect(element).toHaveStyle({
        width: `${size * TILE_SIZE}px`,
        height: `${size * TILE_SIZE}px`,
      })
      unmount()
    })
  })
})
