import React, { useState, useEffect } from 'react';
import useGameStore from '../store/useGameStore';
import CardDisplay from './CardDisplay';
import SwipeHandler from './SwipeHandler';

export default function CardFeed() {
  const { cards, currentIndex, processSwipe, showQuiz, activePowerups } = useGameStore();
  const [flipKey, setFlipKey] = useState(0);
  const [rerolling, setRerolling] = useState(false);
  const [luckyReveal, setLuckyReveal] = useState(false);

  const currentCard = cards[currentIndex];
  const nextCards = [cards[currentIndex + 1], cards[currentIndex + 2]].filter(Boolean);

  useEffect(() => {
    setFlipKey(k => k + 1);
  }, [currentIndex]);

  useEffect(() => {
    if (activePowerups.includes('REROLL')) {
      setRerolling(true);
      setTimeout(() => setRerolling(false), 400);
    }
  }, [activePowerups]);

  useEffect(() => {
    if (activePowerups.includes('LUCKY_DRAW') && currentIndex === 0 && currentCard) {
      setLuckyReveal(true);
      const timer = setTimeout(() => setLuckyReveal(false), 1000);
      return () => clearTimeout(timer);
    }
    setLuckyReveal(false);
  }, [activePowerups, currentIndex, currentCard]);

  if (showQuiz || !currentCard) return null;

  const cardAnimClass = rerolling ? 'reroll-spin' : 'card-flip-enter';
  const luckyClass = luckyReveal ? 'lucky-draw-reveal' : '';

  return (
    <div data-testid="card-feed" className="w-full h-full relative">
      {nextCards.map((card, i) => (
        <div
          key={`stack-${currentIndex + i + 1}`}
          className="absolute inset-0 pointer-events-none"
          style={{
            transform: `scale(${0.97 - i * 0.03}) translateY(${(i + 1) * 4}px)`,
            opacity: 0.4 - i * 0.15,
            zIndex: 1,
          }}
          aria-hidden="true"
        >
          <CardDisplay card={card} totalCards={cards.length} currentIndex={currentIndex + i + 1} />
        </div>
      ))}
      <div className="relative z-[2] w-full h-full" style={{ perspective: '1000px' }}>
        <SwipeHandler onSwipe={processSwipe}>
          <div key={flipKey} className={`${cardAnimClass} ${luckyClass} w-full h-full`}>
            <CardDisplay card={currentCard} totalCards={cards.length} currentIndex={currentIndex} />
          </div>
        </SwipeHandler>
        {luckyReveal && (
          <div data-testid="lucky-draw-overlay" className="absolute inset-0 flex items-center justify-center pointer-events-none z-30">
            <div className="text-4xl font-bold font-zero text-yellow-400 uppercase tracking-widest lucky-draw-reveal" style={{ textShadow: '0 0 20px rgba(255,215,0,0.8)' }}>
              LUCKY DRAW!
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
