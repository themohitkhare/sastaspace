import React, { useEffect, useState, useRef } from 'react';
import useGameStore from '../store/useGameStore';
import CardFeed from '../components/CardFeed';
import ShardBar from '../components/ShardBar';
import QuizCard from '../components/QuizCard';
import PowerupPanel from '../components/PowerupPanel';
import MilestonePopup from '../components/MilestonePopup';
import BreakSuggestion from '../components/BreakSuggestion';

const SHARD_MAP = {
  CREATION: { icon: '\u2726', color: 'text-amber-500' },
  PROTECTION: { icon: '\u25C6', color: 'text-blue-400' },
  DESTRUCTION: { icon: '\u2715', color: 'text-red-500' },
  ENERGY: { icon: '\u2600', color: 'text-yellow-400' },
  POWER: { icon: '\u2B1F', color: 'text-purple-500' },
};

export default function GameFeed() {
  const { fetchStage, isLoading, showQuiz, cards, lastSwipeResult, activePowerups } = useGameStore();
  const [showPowerups, setShowPowerups] = useState(false);
  const [burstParticles, setBurstParticles] = useState([]);
  const [combo, setCombo] = useState({ count: 0, type: null });
  const [showCombo, setShowCombo] = useState(false);
  const [stageBanner, setStageBanner] = useState(null);
  const prevSwipeRef = useRef(null);

  useEffect(() => {
    if (cards.length === 0 && !isLoading) fetchStage();
  }, []);

  useEffect(() => {
    if (!lastSwipeResult || lastSwipeResult === prevSwipeRef.current) return;
    prevSwipeRef.current = lastSwipeResult;
    const { direction, card } = lastSwipeResult;
    if (direction === 'DOWN' && card) {
      const particles = card.types.map((type, i) => ({
        id: `${Date.now()}-${i}`, type,
        icon: SHARD_MAP[type]?.icon || '?',
        color: SHARD_MAP[type]?.color || 'text-white',
      }));
      setBurstParticles(particles);
      setTimeout(() => setBurstParticles([]), 700);
      const primaryType = card.types[0];
      setCombo(prev => {
        if (prev.type === primaryType) {
          const newCount = prev.count + 1;
          if (newCount >= 2) { setShowCombo(true); setTimeout(() => setShowCombo(false), 600); }
          return { count: newCount, type: primaryType };
        }
        return { count: 1, type: primaryType };
      });
    } else {
      setCombo({ count: 0, type: null });
    }
  }, [lastSwipeResult]);

  useEffect(() => {
    if (showQuiz && cards.length > 0) {
      const stageNum = useGameStore.getState().stageNumber;
      setStageBanner(stageNum);
      setTimeout(() => setStageBanner(null), 2200);
    }
  }, [showQuiz, cards.length]);

  if (isLoading && cards.length === 0) {
    return (
      <div data-testid="game-loading" role="status" className="flex-1 flex items-center justify-center bg-black text-white">
        <p className="text-xl font-bold font-zero animate-pulse">LOADING...</p>
      </div>
    );
  }

  return (
    <div data-testid="game-feed" className="flex-1 flex flex-col overflow-hidden">
      <ShardBar />
      {activePowerups.includes('FUSION_BOOST') && (
        <div data-testid="fusion-active-banner" className="bg-sasta-accent text-black text-xs font-bold font-zero text-center py-1 uppercase tracking-wider">FUSION ACTIVE</div>
      )}
      <div className="flex-1 relative">
        {showQuiz ? <QuizCard /> : <CardFeed />}
        {burstParticles.map(p => (
          <div key={p.id} className={`absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 shard-burst pointer-events-none z-30 ${p.color} text-2xl font-bold`} aria-hidden="true">
            {p.icon}
          </div>
        ))}
        {showCombo && combo.count >= 2 && (
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 combo-flash pointer-events-none z-30 text-sasta-accent text-4xl font-bold font-zero" aria-hidden="true">
            x{combo.count}
          </div>
        )}
        {stageBanner !== null && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-40">
            <div className="stage-banner-enter bg-black border-brutal-lg px-8 py-4 text-center">
              <div className="text-sasta-accent text-xs font-bold font-zero tracking-widest uppercase mb-1">STAGE</div>
              <div className="text-white text-5xl font-bold font-zero">{stageBanner}</div>
              <div className="text-sasta-accent text-sm font-bold font-zero tracking-widest uppercase mt-1">COMPLETE</div>
            </div>
          </div>
        )}
        {!showQuiz && (
          <button data-testid="powerup-button" aria-label="Open powerups panel"
            className="absolute bottom-4 right-4 w-12 h-12 bg-black text-sasta-accent border-brutal-sm font-bold font-zero text-xl flex items-center justify-center z-10 hover:bg-sasta-accent hover:text-black transition-colors"
            onClick={() => setShowPowerups(true)}>{'\u26A1'}</button>
        )}
      </div>
      <PowerupPanel isOpen={showPowerups} onClose={() => setShowPowerups(false)} />
      <MilestonePopup />
      <BreakSuggestion />
    </div>
  );
}
