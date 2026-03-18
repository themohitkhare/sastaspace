import React from 'react';
import useGameStore from '../store/useGameStore';

export default function BreakSuggestion() {
  const { showBreak, dismissBreak, fetchStage, sessionStages } = useGameStore();

  if (!showBreak) return null;

  return (
    <div data-testid="break-suggestion" className="fixed inset-0 z-40 flex items-center justify-center">
      <div className="absolute inset-0 bg-black bg-opacity-70" />
      <div className="relative bg-black text-white border-4 border-white p-8 max-w-sm text-center">
        <h3 className="text-xl font-bold mb-3">Nice session!</h3>
        <p className="text-sm mb-6 opacity-70">
          You've completed {sessionStages} stages. Take a break?
        </p>
        <div className="flex gap-3 justify-center">
          <button
            data-testid="break-continue"
            className="px-4 py-2 bg-white text-black font-bold border-2 border-white"
            onClick={() => { dismissBreak(); fetchStage(); }}
          >
            CONTINUE
          </button>
          <button
            data-testid="break-rest"
            className="px-4 py-2 border-2 border-white font-bold hover:bg-white hover:text-black"
            onClick={dismissBreak}
          >
            REST
          </button>
        </div>
      </div>
    </div>
  );
}
