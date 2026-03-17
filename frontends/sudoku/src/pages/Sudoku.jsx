import { useState, useEffect, useRef, useCallback } from 'react';
import PlayerBoard from '../components/PlayerBoard.jsx';
import AiBoard from '../components/AiBoard.jsx';
import SudokuHUD from '../components/SudokuHUD.jsx';
import EndGameModal from '../components/EndGameModal.jsx';
import { parsePastedBoard } from '../utils/sudokuOcr.js';

const API = '/api/v1/sudoku';

export default function Sudoku() {
  const [matchId, setMatchId] = useState(null);
  const [startingBoard, setStartingBoard] = useState([]);
  const [playerBoard, setPlayerBoard] = useState([]);
  const [gridSize, setGridSize] = useState(9);
  const [difficulty, setDifficulty] = useState('medium');
  const [status, setStatus] = useState('idle');
  const [loading, setLoading] = useState(false);

  // AI state
  const [generation, setGeneration] = useState(0);
  const [fitness, setFitness] = useState(0);
  const [heatmap, setHeatmap] = useState([]);
  const [bestBoard, setBestBoard] = useState([]);

  const timerRef = useRef(null);

  // ---- API helpers ----

  const startMatch = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/matches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ difficulty, grid_size: gridSize }),
      });
      const data = await res.json();
      setMatchId(data.match_id);
      setStartingBoard(data.starting_board);
      setPlayerBoard([...data.starting_board]);
      setGridSize(data.grid_size);
      setStatus('in_progress');
      setGeneration(0);
      setFitness(0);
      setHeatmap(new Array(data.grid_size * data.grid_size).fill(0));
      setBestBoard(new Array(data.grid_size * data.grid_size).fill(0));
    } catch (err) {
      console.error('Failed to start match', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAiState = useCallback(async (id) => {
    try {
      const res = await fetch(`${API}/matches/${id}`);
      const data = await res.json();
      setGeneration(data.ai.generation_count);
      setFitness(data.ai.fitness_score);
      setHeatmap(data.ai.heatmap_data);
      setBestBoard(data.ai.best_board);
      if (data.status !== 'in_progress') {
        setStatus(data.status);
      }
    } catch {
      /* polling failure — ignore */
    }
  }, []);

  const triggerAiTick = useCallback(async (id) => {
    try {
      const res = await fetch(`${API}/matches/${id}/ai-tick`, { method: 'POST' });
      const data = await res.json();
      setGeneration(data.generation_count);
      setFitness(data.fitness_score);
      if (data.status !== 'in_progress') {
        setStatus(data.status);
      }
      // Refresh full state (heatmap etc)
      await fetchAiState(id);
    } catch {
      /* tick failure — retry on next interval */
    }
  }, [fetchAiState]);

  // AI tick polling
  useEffect(() => {
    if (!matchId || status !== 'in_progress') {
      clearInterval(timerRef.current);
      return;
    }
    timerRef.current = setInterval(() => triggerAiTick(matchId), 1200);
    // Trigger first tick immediately
    triggerAiTick(matchId);
    return () => clearInterval(timerRef.current);
  }, [matchId, status, triggerAiTick]);

  // ---- Handlers ----

  const handleCellChange = (idx, val) => {
    const next = [...playerBoard];
    next[idx] = val;
    setPlayerBoard(next);
    // Save to server (fire-and-forget)
    if (matchId) {
      fetch(`${API}/matches/${matchId}/board`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ board: next }),
      }).catch(() => {});
    }
  };

  const handleClaimVictory = async () => {
    if (!matchId) return;
    try {
      const res = await fetch(`${API}/matches/${matchId}/claim-victory`, { method: 'POST' });
      const data = await res.json();
      if (data.valid) {
        setStatus('player_won');
      }
    } catch (err) {
      console.error('Claim failed', err);
    }
  };

  const handlePaste = (e) => {
    const text = e.clipboardData.getData('text');
    const board = parsePastedBoard(text, gridSize);
    if (board) {
      // Merge: keep clues, replace editable cells
      const merged = startingBoard.map((clue, i) => (clue !== 0 ? clue : board[i]));
      setPlayerBoard(merged);
    }
  };

  const handlePlayAgain = () => {
    setMatchId(null);
    setStatus('idle');
    setStartingBoard([]);
    setPlayerBoard([]);
    setGeneration(0);
    setFitness(0);
    setHeatmap([]);
    setBestBoard([]);
  };

  // ---- Render ----

  const isGameOver = status === 'player_won' || status === 'ai_won';

  return (
    <div className="page" onPaste={handlePaste}>
      {status === 'idle' && (
        <div className="start-screen">
          <h2>Sudoku vs. Genetic Algorithm</h2>
          <p>
            Race against an AI powered by a genetic algorithm with 13 mutation
            operators, tabu dedup, and stall detection. Can you solve the puzzle
            before evolution catches up?
          </p>
          <div className="difficulty-picker">
            {['easy', 'medium', 'hard'].map((d) => (
              <button
                key={d}
                className={`difficulty-btn ${difficulty === d ? 'active' : ''}`}
                onClick={() => setDifficulty(d)}
              >
                {d.charAt(0).toUpperCase() + d.slice(1)}
              </button>
            ))}
          </div>
          <button
            className="btn-primary"
            onClick={startMatch}
            disabled={loading}
            id="start-match-btn"
          >
            {loading ? 'Starting…' : 'Start Race'}
          </button>
        </div>
      )}

      {status !== 'idle' && (
        <>
          <SudokuHUD generation={generation} fitness={fitness} status={status} />

          <div className="boards-container">
            <PlayerBoard
              board={playerBoard}
              startingBoard={startingBoard}
              gridSize={gridSize}
              onChange={handleCellChange}
              disabled={isGameOver}
            />
            <AiBoard
              bestBoard={bestBoard}
              startingBoard={startingBoard}
              heatmapData={heatmap}
              gridSize={gridSize}
            />
          </div>

          {!isGameOver && (
            <div className="actions-row">
              <button className="btn-primary" onClick={handleClaimVictory} id="claim-victory-btn">
                Claim Victory
              </button>
              <button className="btn-secondary" onClick={handlePlayAgain}>
                New Game
              </button>
            </div>
          )}

          {isGameOver && (
            <EndGameModal status={status} onPlayAgain={handlePlayAgain} />
          )}
        </>
      )}
    </div>
  );
}
