import React, { useRef, useState, useCallback } from 'react';

const SWIPE_THRESHOLD = 50;

const DIRECTION_LABELS = {
  UP: '▲ PLAY',
  DOWN: '▼ SYNTHESIZE',
  LEFT: '◀ SHARE',
  RIGHT: '▶ SAVE',
};

export default function SwipeHandler({ children, onSwipe, disabled }) {
  const startPos = useRef(null);
  const [dragDelta, setDragDelta] = useState({ x: 0, y: 0 });
  const [activeDirection, setActiveDirection] = useState(null);

  const getDirection = useCallback((dx, dy) => {
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);
    if (absDx < SWIPE_THRESHOLD && absDy < SWIPE_THRESHOLD) return null;
    if (absDy > absDx) return dy < 0 ? 'UP' : 'DOWN';
    return dx < 0 ? 'LEFT' : 'RIGHT';
  }, []);

  const handleStart = useCallback((x, y) => {
    startPos.current = { x, y };
    setDragDelta({ x: 0, y: 0 });
  }, []);

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

    if (dir && onSwipe) {
      onSwipe(dir);
    }
  }, [activeDirection, onSwipe, disabled]);

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

  const transform = `translate(${dragDelta.x * 0.3}px, ${dragDelta.y * 0.3}px)`;

  return (
    <div
      data-testid="swipe-handler"
      className="relative w-full h-full select-none touch-none"
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseUp}
    >
      <div style={{ transform, transition: dragDelta.x === 0 && dragDelta.y === 0 ? 'transform 0.2s' : 'none' }}>
        {children}
      </div>

      {/* Direction indicator */}
      {activeDirection && (
        <div
          data-testid="swipe-direction"
          className="absolute inset-0 flex items-center justify-center pointer-events-none"
        >
          <div className="bg-black bg-opacity-70 text-white px-6 py-3 text-xl font-bold tracking-wider">
            {DIRECTION_LABELS[activeDirection]}
          </div>
        </div>
      )}
    </div>
  );
}
