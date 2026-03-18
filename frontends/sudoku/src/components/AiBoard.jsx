import React from 'react';
import UnifiedBoard from './UnifiedBoard.jsx';

/**
 * AiBoard — Read-only view of the GA's best board with heatmap overlay.
 *
 * Props:
 *   bestBoard: number[]
 *   startingBoard: number[]
 *   heatmapData: number[]
 *   gridSize: number
 */
export default function AiBoard({ bestBoard, startingBoard, heatmapData, gridSize }) {
  return (
    <div className="board-panel" data-testid="ai-board">
      <h3>
        <span className="dot dot-ai" /> AI Solver
      </h3>
      <UnifiedBoard
        board={bestBoard}
        startingBoard={startingBoard}
        heatmapData={heatmapData}
        gridSize={gridSize}
        status="in_progress"
        // No-op: AI board is read-only from the user's perspective.
        onChange={() => {}}
      />
    </div>
  );
}

