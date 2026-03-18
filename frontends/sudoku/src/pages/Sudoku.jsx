import { useState, useEffect, useRef, useCallback } from 'react';
import PlayerBoard from '../components/PlayerBoard.jsx';
import AiBoard from '../components/AiBoard.jsx';
import SudokuHUD from '../components/SudokuHUD.jsx';
import EndGameModal from '../components/EndGameModal.jsx';
import { parsePastedBoard } from '../utils/sudokuOcr.js';

const API = '/api/v1/sudoku';
const OCR_UNCERTAIN_THRESHOLD = 0.6;

export default function Sudoku() {
  const [matchId, setMatchId] = useState(null);
  const [startingBoard, setStartingBoard] = useState([]);
  const [playerBoard, setPlayerBoard] = useState([]);
  const [ocrConfidences, setOcrConfidences] = useState(new Array(81).fill(0));
  const [showOcrReview, setShowOcrReview] = useState(false);
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
  const fileInputRef = useRef(null);

  // ---- API helpers ----

  const startMatch = async () => {
    setLoading(true);
    try {
      const custom_board =
        playerBoard?.length === gridSize * gridSize && playerBoard.some((c) => c !== 0)
          ? playerBoard
          : null;
      const res = await fetch(`${API}/matches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ difficulty, grid_size: gridSize, custom_board }),
      });
      const data = await res.json();
      setMatchId(data.match_id);
      setStartingBoard(data.starting_board);
      setPlayerBoard([...data.starting_board]);
      setGridSize(data.grid_size);
      setStatus('in_progress');
      setShowOcrReview(false);
      setOcrConfidences(new Array(data.grid_size * data.grid_size).fill(0));
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

  const setBoardFromOcr = (board, confidences) => {
    if (!Array.isArray(board) || board.length !== gridSize * gridSize) return;

    setPlayerBoard(board);

    const conf =
      Array.isArray(confidences) && confidences.length === board.length
        ? confidences.map((c) => {
            const n = Number(c);
            if (Number.isNaN(n)) return 0;
            return Math.max(0, Math.min(1, n));
          })
        : board.map((v) => (v ? 1 : 0));

    setOcrConfidences(conf);
    setShowOcrReview(true);
  };

  const handleUploadImage = async (file) => {
    if (!file || !file.type?.startsWith('image/')) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API}/extract-board`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err?.detail || 'OCR failed');
      }
      const data = await res.json();
      setBoardFromOcr(data.board, data.confidences);
    } catch (err) {
      console.error('OCR failed:', err);
      alert('Failed to extract Sudoku board from image.');
    } finally {
      setLoading(false);
    }
  };

  const onFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (file) await handleUploadImage(file);
    e.target.value = '';
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

  const handlePaste = useCallback(
    async (e) => {
      const items = e.clipboardData?.items || [];
      let imageFile = null;

      for (let i = 0; i < items.length; i++) {
        if (items[i].type?.includes('image')) {
          imageFile = items[i].getAsFile();
          break;
        }
      }

      if (imageFile) {
        await handleUploadImage(imageFile);
        return;
      }

      const text = e.clipboardData?.getData('text') || '';
      const board = parsePastedBoard(text, gridSize);
      if (board) {
        setPlayerBoard(board);
      }
    },
    [gridSize],
  );

  useEffect(() => {
    const onWindowPaste = (e) => {
      // Only enable OCR paste before game ends; during game, keep current behavior.
      if (status === 'player_won' || status === 'ai_won') return;
      handlePaste(e);
    };
    window.addEventListener('paste', onWindowPaste);
    return () => window.removeEventListener('paste', onWindowPaste);
  }, [handlePaste, status]);

  const handlePlayAgain = () => {
    setMatchId(null);
    setStatus('idle');
    setStartingBoard([]);
    setPlayerBoard([]);
    setOcrConfidences(new Array(81).fill(0));
    setShowOcrReview(false);
    setGeneration(0);
    setFitness(0);
    setHeatmap([]);
    setBestBoard([]);
  };

  // ---- Render ----

  const isGameOver = status === 'player_won' || status === 'ai_won';
  const uncertainCells =
    showOcrReview && playerBoard.length
      ? playerBoard.map(
          (v, i) => Boolean(v) && (ocrConfidences[i] ?? 0) < OCR_UNCERTAIN_THRESHOLD,
        )
      : [];
  const detectedCount = showOcrReview ? playerBoard.filter((v) => v !== 0).length : 0;
  const uncertainCount = showOcrReview ? uncertainCells.filter(Boolean).length : 0;

  return (
    <div className="page">
      {status === 'idle' && (
        <div className="start-screen">
          <h2>Sudoku vs. Genetic Algorithm</h2>
          <p>
            Race against an AI powered by a genetic algorithm with 13 mutation
            operators, tabu dedup, and stall detection. Can you solve the puzzle
            before evolution catches up?
          </p>
          <p style={{ maxWidth: 520 }}>
            Paste an image (or upload a screenshot) to autofill the puzzle. If OCR is unsure, those
            digits will be highlighted for quick correction.
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
          <div className="boards-container" style={{ gridTemplateColumns: '1fr' }}>
            <PlayerBoard
              board={playerBoard.length ? playerBoard : new Array(gridSize * gridSize).fill(0)}
              startingBoard={new Array(gridSize * gridSize).fill(0)}
              gridSize={gridSize}
              onChange={handleCellChange}
              disabled={loading}
              uncertainCells={uncertainCells}
            />
          </div>

          {showOcrReview && (
            <div className="actions-row" style={{ gap: '0.75rem' }}>
              <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                OCR detected <b>{detectedCount}</b> digits; <b>{uncertainCount}</b> uncertain.
              </div>
              <button
                className="btn-secondary"
                onClick={() => {
                  const next = playerBoard.map((v, i) => (uncertainCells[i] ? 0 : v));
                  setPlayerBoard(next);
                }}
                disabled={loading || uncertainCount === 0}
              >
                Clear uncertain
              </button>
              <button className="btn-secondary" onClick={() => setShowOcrReview(false)} disabled={loading}>
                Accept OCR
              </button>
            </div>
          )}

          <div className="actions-row" style={{ gap: '0.75rem' }}>
            <button
              className="btn-secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
            >
              Upload image
            </button>
            <button
              className="btn-primary"
              onClick={startMatch}
              disabled={loading}
              id="start-match-btn"
            >
              {loading ? 'Starting…' : 'Start Race'}
            </button>
            <button className="btn-secondary" onClick={handlePlayAgain} disabled={loading}>
              Clear
            </button>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={onFileChange}
          />
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
