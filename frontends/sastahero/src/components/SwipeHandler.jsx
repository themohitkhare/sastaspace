import React, { useRef, useState, useCallback, useEffect } from 'react';

const SWIPE_THRESHOLD = 50;

const DIRECTION_LABELS = {
  UP: '\u25B2 PLAY',
  DOWN: '\u25BC SYNTHESIZE',
  LEFT: '\u25C0 SHARE',
  RIGHT: '\u25B6 SAVE',
};

const KEY_MAP = {
  ArrowUp: 'UP',
  ArrowDown: 'DOWN',
  ArrowLeft: 'LEFT',
  ArrowRight: 'RIGHT',
  w: 'UP',
  s: 'DOWN',
  a: 'LEFT',
  d: 'RIGHT',
};

export default function SwipeHandler({ children, onSwipe, disabled }) {
  const startPos = useRef(null);
  const [dragDelta, setDragDelta] = useState({ x: 0, y: 0 });
  const [activeDirection, setActiveDirection] = useState(null);
  const [exitDirection, setExitDirection] = useState(null);
  const containerRef = useRef(null);

  const getDirection = useCallback((dx, dy) => {
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);
    if (absDx < SWIPE_THRESHOLD && absDy < SWIPE_THRESHOLD) return null;
    if (absDy > absDx) return dy < 0 ? 'UP' : 'DOWN';
    return dx < 0 ? 'LEFT' : 'RIGHT';
  }, []);

  const triggerSwipe = useCallback((dir) => {
    if (disabled || !dir) return;
    setExitDirection(dir);
    setTimeout(() => {
      setExitDirection(null);
      if (onSwipe) onSwipe(dir);
    }, 300);
  }, [disabled, onSwipe]);

  const handleStart = useCallback((x, y) => {
    if (exitDirection) return;
    startPos.current = { x, y };
    setDragDelta({ x: 0, y: 0 });
  }, [exitDirection]);

  const handleMove = useCallback((x, y) => {
    if (!startPos.current) return;
    const dx = x - startPos.current.x;
    const dy = y - startPos.current.y;
    setDragDelta({ x: dx, y: dy });
    setActiveDirection(getDirection(dx, dy));
  }, [getDirection]);

  const handleEnd = useCallback(() => {
    if (!startPos.current || disabled) {
      startPos.current = null;
      setDragDelta({ x: 0, y: 0 });
      setActiveDirection(null);
      return;
    }

    const dir = activeDirection;
    startPos.current = null;
    setDragDelta({ x: 0, y: 0 });
    setActiveDirection(null);

    if (dir) {
      triggerSwipe(dir);
    }
  }, [activeDirection, triggerSwipe, disabled]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (disabled || exitDirection) return;
      const dir = KEY_MAP[e.key];
      if (dir) {
        e.preventDefault();
        triggerSwipe(dir);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [disabled, exitDirection, triggerSwipe]);

  // Touch events
  const onTouchStart = (e) => {
    const t = e.touches[0];
    handleStart(t.clientX, t.clientY);
  };
  const onTouchMove = (e) => {
    const t = e.touches[0];
    handleMove(t.clientX, t.clientY);
  };
  const onTouchEnd = () => handleEnd();

  // Mouse events
  const onMouseDown = (e) => handleStart(e.clientX, e.clientY);
  const onMouseMove = (e) => {
    if (startPos.current) handleMove(e.clientX, e.clientY);
  };
  const onMouseUp = () => handleEnd();

  const dragTransform = exitDirection
    ? ''
    : `translate(${dragDelta.x * 0.3}px, ${dragDelta.y * 0.3}px)`;
  const exitClass = exitDirection ? `card-exit-${exitDirection}` : '';
  const enterClass = !exitDirection && dragDelta.x === 0 && dragDelta.y === 0 ? 'card-enter' : '';

  return (
    <div
      ref={containerRef}
      data-testid="swipe-handler"
      role="application"
      aria-label="Card swipe area. Use arrow keys or WASD to swipe: Up to play, Down to synthesize, Left to share, Right to save"
      tabIndex={0}
      className="relative w-full h-full select-none touch-none outline-none"
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    >
      <div
        className={`${exitClass} ${enterClass}`}
        style={{
          transform: dragTransform,
          transition: !exitDirection && dragDelta.x === 0 && dragDelta.y === 0 ? 'transform 0.2s' : 'none',
        }}
      >
        {children}
      </div>

      {/* Direction indicator */}
      {activeDirection && !exitDirection && (
        <div
          data-testid="swipe-direction"
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
          aria-live="polite"
        >
          <div className="bg-black bg-opacity-70 text-white px-6 py-3 text-xl font-bold tracking-wider">
            {DIRECTION_LABELS[activeDirection]}
          </div>
        </div>
      )}
    </div>
  );
}
