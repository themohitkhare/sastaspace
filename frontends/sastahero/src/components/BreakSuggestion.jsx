import React from 'react';
import useGameStore from '../store/useGameStore';

export default function BreakSuggestion() {
  const { showBreak, dismissBreak, fetchStage, sessionStages } = useGameStore();

  if (!showBreak) return null;

  return (
    <div data-testid="break-suggestion" role="dialog" aria-label="Break suggestion" className="fixed inset-0 z-40 flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-80" aria-hidden="true" />
      <div className="relative bg-black text-white border-brutal-lg border-sasta-accent p-8 max-w-sm text-center">
        <h3 className="text-xl font-bold font-zero uppercase tracking-widest mb-3">NICE SESSION!</h3>
        <p className="text-sm font-zero mb-6 opacity-70">{sessionStages} STAGES COMPLETED. TAKE A BREAK?</p>
        <div className="flex gap-3 justify-center">
          <button data-testid="break-continue" className="px-4 py-2 bg-sasta-accent text-black font-bold font-zero border-brutal-sm hover:bg-white transition-colors" onClick={() => { dismissBreak(); fetchStage(); }}>CONTINUE</button>
          <button data-testid="break-rest" className="px-4 py-2 bg-black text-white font-bold font-zero border-brutal-sm hover:bg-sasta-accent hover:text-black transition-colors" onClick={dismissBreak}>REST</button>
        </div>
      </div>
    </div>
  );
}
