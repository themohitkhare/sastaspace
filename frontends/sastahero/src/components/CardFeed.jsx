import React from 'react';
import useGameStore from '../store/useGameStore';
import CardDisplay from './CardDisplay';
import SwipeHandler from './SwipeHandler';

export default function CardFeed() {
  const { cards, currentIndex, processSwipe, showQuiz } = useGameStore();

  const currentCard = cards[currentIndex];

  if (showQuiz || !currentCard) return null;

  return (
    <div data-testid="card-feed" className="w-full h-full">
      <SwipeHandler onSwipe={processSwipe}>
        <CardDisplay
          card={currentCard}
          totalCards={cards.length}
          currentIndex={currentIndex}
        />
      </SwipeHandler>
    </div>
  );
}
