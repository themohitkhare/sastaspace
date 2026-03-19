import React, { useEffect, useState } from 'react';
import useGameStore from '../store/useGameStore';

export default function MilestonePopup() {
  const { milestone, dismissMilestone } = useGameStore();
  const [showFlash, setShowFlash] = useState(false);

  useEffect(() => {
    if (milestone) {
      setShowFlash(true);
      setTimeout(() => setShowFlash(false), 150);
      const timer = setTimeout(dismissMilestone, 5000);
      return () => clearTimeout(timer);
    }
  }, [milestone, dismissMilestone]);

  if (!milestone) return null;

  return (
    <div data-testid="milestone-popup" role="alert" aria-label={`Milestone reached: ${milestone.message}`} className="fixed inset-0 z-50 flex items-center justify-center" onClick={dismissMilestone}>
      {showFlash && (<div className="absolute inset-0 bg-white milestone-flash z-[51]" aria-hidden="true" />)}
      <div className="absolute inset-0 bg-black bg-opacity-80" />
      <div className="relative">
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none" aria-hidden="true">
          <div className="w-16 h-16 rounded-full border-yellow-400 milestone-ring" />
        </div>
        <div className="relative milestone-badge-enter bg-black text-white border-brutal-lg border-yellow-400 p-8 max-w-sm text-center z-[25]">
          <div className="text-5xl mb-4">{'\u2726'}</div>
          <h3 className="text-2xl font-bold font-zero uppercase tracking-widest mb-2">MILESTONE</h3>
          <p className="text-lg font-zero">{milestone.message}</p>
          {milestone.badge && (<p className="mt-2 text-yellow-400 text-sm font-zero font-bold uppercase">BADGE: {milestone.badge}</p>)}
          <p className="mt-4 text-xs opacity-40 font-zero">TAP TO DISMISS</p>
        </div>
      </div>
    </div>
  );
}
