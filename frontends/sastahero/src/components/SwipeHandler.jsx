import React, { useRef, useState, useCallback, useEffect } from 'react';

const SWIPE_THRESHOLD = 50;

const DIRECTION_LABELS = {
  UP: '\u25B2 PLAY',
  DOWN: '\u25BC SYNTHESIZE',
  LEFT: '\u25C0 SHARE',
  RIGHT: '\u25B6 SAVE',
};

const KEY_MAP = {
  ArrowUp: 'UP', ArrowDown: 'DOWN', ArrowLeft: 'LEFT', ArrowRight: 'RIGHT',
  w: 'UP', s: 'DOWN', a: 'LEFT', d: 'RIGHT',
};

export default function SwipeHandler({ children, onSwipe, disabled }) {
  const startPos = useRef(null);
  const [dragDelta, setDragDelta] = useState({ x: 0, y: 0 });
  const [activeDirection, setActiveDirection] = useState(null);
  const [exitDirection, setExitDirection] = useState(null);
  const [labelPopped, setLabelPopped] = useState(false);
  const [isIdle, setIsIdle] = useState(false);
  const idleTimer = useRef(null);
  const containerRef = useRef(null);

  const resetIdleTimer = useCallback(() => {
    setIsIdle(false);
    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => setIsIdle(true), 3000);
  }, []);

  useEffect(() => {
    resetIdleTimer();
    return () => { if (idleTimer.current) clearTimeout(idleTimer.current); };
  }, [resetIdleTimer]);

  const getDirection = useCallback((dx, dy) => {
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);
    if (absDx < SWIPE_THRESHOLD && absDy < SWIPE_THRESHOLD) return null;
    if (absDy > absDx) return dy < 0 ? 'UP' : 'DOWN';
    return dx < 0 ? 'LEFT' : 'RIGHT';
  }, []);

  const triggerSwipe = useCallback((dir) => {
    if (disabled || !dir) return;
    resetIdleTimer();
    setExitDirection(dir);
    setLabelPopped(false);
    setTimeout(() => {
      setExitDirection(null);
      if (onSwipe) onSwipe(dir);
    }, 300);
  }, [disabled, onSwipe, resetIdleTimer]);

  const handleStart = useCallback((x, y) => {
    if (exitDirection) return;
    resetIdleTimer();
    startPos.current = { x, y };
    setDragDelta({ x: 0, y: 0 });
  }, [exitDirection, resetIdleTimer]);

  const handleMove = useCallback((x, y) => {
    if (!startPos.current) return;
    const dx = x - startPos.current.x;
    const dy = y - startPos.current.y;
    setDragDelta({ x: dx, y: dy });
    const dir = getDirection(dx, dy);
    if (dir && !activeDirection) {
      setLabelPopped(true);
    }
    setActiveDirection(dir);
  }, [getDirection, activeDirection]);

  const handleEnd = useCallback(() => {
    if (!startPos.current || disabled) {
      startPos.current = null;
      setDragDelta({ x: 0, y: 0 });
      setActiveDirection(null);
      setLabelPopped(false);
      return;
    }
    const dir = activeDirection;
    startPos.current = null;
    setDragDelta({ x: 0, y: 0 });
    setActiveDirection(null);
    setLabelPopped(false);
    if (dir) triggerSwipe(dir);
  }, [activeDirection, triggerSwipe, disabled]);

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (disabled || exitDirection) return;
      const dir = KEY_MAP[e.key];
      if (dir) { e.preventDefault(); triggerSwipe(dir); }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [disabled, exitDirection, triggerSwipe]);

  const onTouchStart = (e) => { const t = e.touches[0]; handleStart(t.clientX, t.clientY); };
  const onTouchMove = (e) => { const t = e.touches[0]; handleMove(t.clientX, t.clientY); };
  const onTouchEnd = () => handleEnd();
  const onMouseDown = (e) => handleStart(e.clientX, e.clientY);
  const onMouseMove = (e) => { if (startPos.current) handleMove(e.clientX, e.clientY); };
  const onMouseUp = () => handleEnd();

  const isDragging = startPos.current !== null && (dragDelta.x !== 0 || dragDelta.y !== 0);
  const dragTransform = exitDirection ? '' : `translate(${dragDelta.x * 0.3}px, ${dragDelta.y * 0.3}px)`;
  const exitClass = exitDirection ? `card-exit-${exitDirection}` : '';
  const enterClass = !exitDirection && dragDelta.x === 0 && dragDelta.y === 0 ? 'card-enter' : '';
  const breatheClass = isIdle && !exitDirection && !isDragging ? 'card-breathe' : '';

  return (
    <div
      ref={containerRef}
      data-testid="swipe-handler"
      role="application"
      aria-label="Card swipe area. Use arrow keys or WASD to swipe: Up to play, Down to synthesize, Left to share, Right to save"
      tabIndex={0}
      className="relative w-full h-full select-none touch-none outline-none"
      onTouchStart={onTouchStart} onTouchMove={onTouchMove} onTouchEnd={onTouchEnd}
      onMouseDown={onMouseDown} onMouseMove={onMouseMove} onMouseUp={onMouseUp} onMouseLeave={onMouseUp}
    >
      {isDragging && !exitDirection && (
        <div className="absolute inset-0 pointer-events-none opacity-15 z-0" aria-hidden="true">
          {children}
        </div>
      )}
      <div
        className={`${exitClass} ${enterClass} ${breatheClass}`}
        style={{
          transform: dragTransform,
          transition: !exitDirection && dragDelta.x === 0 && dragDelta.y === 0 ? 'transform 0.2s' : 'none',
        }}
      >
        {children}
      </div>
      {activeDirection && !exitDirection && (
        <div data-testid="swipe-direction" className="absolute inset-0 flex items-center justify-center pointer-events-none z-20" aria-live="polite">
          <div className={`bg-black border-brutal-sm px-6 py-3 text-xl font-bold font-zero tracking-widest text-sasta-accent ${labelPopped ? 'label-pop' : ''}`}>
            {DIRECTION_LABELS[activeDirection]}
          </div>
        </div>
      )}
    </div>
  );
}
