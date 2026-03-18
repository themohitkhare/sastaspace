import React, { useEffect, useState } from 'react';
import useGameStore from '../store/useGameStore';
import CardFeed from '../components/CardFeed';
import ShardBar from '../components/ShardBar';
import QuizCard from '../components/QuizCard';
import PowerupPanel from '../components/PowerupPanel';
import MilestonePopup from '../components/MilestonePopup';
import BreakSuggestion from '../components/BreakSuggestion';

export default function GameFeed() {
  const { fetchStage, isLoading, showQuiz, cards } = useGameStore();
  const [showPowerups, setShowPowerups] = useState(false);

  useEffect(() => {
    if (cards.length === 0 && !isLoading) {
      fetchStage();
    }
  }, []);

  if (isLoading && cards.length === 0) {
    return (
      <div data-testid="game-loading" role="status" className="flex-1 flex items-center justify-center bg-black text-white">
        <p className="text-xl font-bold animate-pulse">Loading...</p>
      </div>
    );
  }

  return (
    <div data-testid="game-feed" className="flex-1 flex flex-col overflow-hidden">
      <ShardBar />

      <div className="flex-1 relative">
        {showQuiz ? <QuizCard /> : <CardFeed />}

        {/* Powerup button */}
        {!showQuiz && (
          <button
            data-testid="powerup-button"
            aria-label="Open powerups panel"
            className="absolute bottom-4 right-4 w-12 h-12 bg-black text-white border-2 border-white font-bold text-xl flex items-center justify-center z-10"
            onClick={() => setShowPowerups(true)}
          >
            {'\u26A1'}
          </button>
        )}
      </div>

      <PowerupPanel isOpen={showPowerups} onClose={() => setShowPowerups(false)} />
      <MilestonePopup />
      <BreakSuggestion />
    </div>
  );
}
