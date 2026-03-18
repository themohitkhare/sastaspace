import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import SwipeHandler from './SwipeHandler';

describe('SwipeHandler', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders children', () => {
    render(
      <SwipeHandler onSwipe={() => {}}>
        <div data-testid="child">Card content</div>
      </SwipeHandler>
    );
    expect(screen.getByTestId('child')).toBeInTheDocument();
  });

  it('renders swipe handler wrapper', () => {
    render(
      <SwipeHandler onSwipe={() => {}}>
        <div>Content</div>
      </SwipeHandler>
    );
    expect(screen.getByTestId('swipe-handler')).toBeInTheDocument();
  });

  it('has proper ARIA attributes', () => {
    render(
      <SwipeHandler onSwipe={() => {}}>
        <div>Content</div>
      </SwipeHandler>
    );
    const handler = screen.getByTestId('swipe-handler');
    expect(handler).toHaveAttribute('role', 'application');
    expect(handler).toHaveAttribute('tabIndex', '0');
  });

  it('calls onSwipe with UP on upward drag', () => {
    const onSwipe = vi.fn();
    render(
      <SwipeHandler onSwipe={onSwipe}>
        <div>Content</div>
      </SwipeHandler>
    );

    const handler = screen.getByTestId('swipe-handler');
    fireEvent.mouseDown(handler, { clientX: 100, clientY: 200 });
    fireEvent.mouseMove(handler, { clientX: 100, clientY: 100 });
    fireEvent.mouseUp(handler);

    act(() => { vi.advanceTimersByTime(300); });
    expect(onSwipe).toHaveBeenCalledWith('UP');
  });

  it('calls onSwipe with DOWN on downward drag', () => {
    const onSwipe = vi.fn();
    render(
      <SwipeHandler onSwipe={onSwipe}>
        <div>Content</div>
      </SwipeHandler>
    );

    const handler = screen.getByTestId('swipe-handler');
    fireEvent.mouseDown(handler, { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(handler, { clientX: 100, clientY: 200 });
    fireEvent.mouseUp(handler);

    act(() => { vi.advanceTimersByTime(300); });
    expect(onSwipe).toHaveBeenCalledWith('DOWN');
  });

  it('calls onSwipe with LEFT on left drag', () => {
    const onSwipe = vi.fn();
    render(
      <SwipeHandler onSwipe={onSwipe}>
        <div>Content</div>
      </SwipeHandler>
    );

    const handler = screen.getByTestId('swipe-handler');
    fireEvent.mouseDown(handler, { clientX: 200, clientY: 100 });
    fireEvent.mouseMove(handler, { clientX: 100, clientY: 100 });
    fireEvent.mouseUp(handler);

    act(() => { vi.advanceTimersByTime(300); });
    expect(onSwipe).toHaveBeenCalledWith('LEFT');
  });

  it('calls onSwipe with RIGHT on right drag', () => {
    const onSwipe = vi.fn();
    render(
      <SwipeHandler onSwipe={onSwipe}>
        <div>Content</div>
      </SwipeHandler>
    );

    const handler = screen.getByTestId('swipe-handler');
    fireEvent.mouseDown(handler, { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(handler, { clientX: 200, clientY: 100 });
    fireEvent.mouseUp(handler);

    act(() => { vi.advanceTimersByTime(300); });
    expect(onSwipe).toHaveBeenCalledWith('RIGHT');
  });

  it('does not call onSwipe when disabled', () => {
    const onSwipe = vi.fn();
    render(
      <SwipeHandler onSwipe={onSwipe} disabled>
        <div>Content</div>
      </SwipeHandler>
    );

    const handler = screen.getByTestId('swipe-handler');
    fireEvent.mouseDown(handler, { clientX: 100, clientY: 200 });
    fireEvent.mouseMove(handler, { clientX: 100, clientY: 100 });
    fireEvent.mouseUp(handler);

    act(() => { vi.advanceTimersByTime(300); });
    expect(onSwipe).not.toHaveBeenCalled();
  });

  it('does not fire on small movements', () => {
    const onSwipe = vi.fn();
    render(
      <SwipeHandler onSwipe={onSwipe}>
        <div>Content</div>
      </SwipeHandler>
    );

    const handler = screen.getByTestId('swipe-handler');
    fireEvent.mouseDown(handler, { clientX: 100, clientY: 100 });
    fireEvent.mouseMove(handler, { clientX: 110, clientY: 110 });
    fireEvent.mouseUp(handler);

    act(() => { vi.advanceTimersByTime(300); });
    expect(onSwipe).not.toHaveBeenCalled();
  });

  it('supports keyboard navigation with arrow keys', () => {
    const onSwipe = vi.fn();
    render(
      <SwipeHandler onSwipe={onSwipe}>
        <div>Content</div>
      </SwipeHandler>
    );

    fireEvent.keyDown(window, { key: 'ArrowUp' });
    act(() => { vi.advanceTimersByTime(300); });
    expect(onSwipe).toHaveBeenCalledWith('UP');
  });

  it('supports WASD keys', () => {
    const onSwipe = vi.fn();
    render(
      <SwipeHandler onSwipe={onSwipe}>
        <div>Content</div>
      </SwipeHandler>
    );

    fireEvent.keyDown(window, { key: 'd' });
    act(() => { vi.advanceTimersByTime(300); });
    expect(onSwipe).toHaveBeenCalledWith('RIGHT');
  });
});
