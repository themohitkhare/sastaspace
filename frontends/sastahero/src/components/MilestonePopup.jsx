import React, { useEffect } from 'react';
import useGameStore from '../store/useGameStore';

export default function MilestonePopup() {
  const { milestone, dismissMilestone } = useGameStore();

  useEffect(() => {
    if (milestone) {
      const timer = setTimeout(dismissMilestone, 5000);
      return () => clearTimeout(timer);
    }
  }, [milestone, dismissMilestone]);

  if (!milestone) return null;

  return (
    <div
      data-testid="milestone-popup"
      className="fixed inset-0 z-50 flex items-center justify-center"
      onClick={dismissMilestone}
    >
      <div className="absolute inset-0 bg-black bg-opacity-70" />
      <div className="relative bg-black text-white border-4 border-yellow-400 p-8 max-w-sm text-center shadow-[0_0_40px_rgba(255,215,0,0.5)]">
        <div className="text-4xl mb-4">🏆</div>
        <h3 className="text-2xl font-bold mb-2">MILESTONE!</h3>
        <p className="text-lg">{milestone.message}</p>
        {milestone.badge && (
          <p className="mt-2 text-yellow-400 text-sm">Badge unlocked: {milestone.badge}</p>
        )}
        <p className="mt-4 text-xs opacity-40">tap to dismiss</p>
      </div>
    </div>
  );
}
