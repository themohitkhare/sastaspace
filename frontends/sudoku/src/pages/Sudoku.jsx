import { useState, useEffect, useRef, useCallback } from 'react';
import PlayerBoard from '../components/PlayerBoard.jsx';
import AiBoard from '../components/AiBoard.jsx';
import SudokuHUD from '../components/SudokuHUD.jsx';
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

  // GA solver state
  const [generation, setGeneration] = useState(0);
  const [fitness, setFitness] = useState(0);
  const [heatmap, setHeatmap] = useState([]);
  const [bestBoard, setBestBoard] = useState([]);

  const timerRef = useRef(null);
  const fileInputRef = useRef(null);

  // ---- API helpers ----

  const startSolving = async () => {
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
      setStatus('solving');
      setShowOcrReview(false);
      setOcrConfidences(new Array(data.grid_size * data.grid_size).fill(0));
      setGeneration(0);
      setFitness(0);
      setHeatmap(new Array(data.grid_size * data.grid_size).fill(0));
      setBestBoard(new Array(data.grid_size * data.grid_size).fill(0));
    } catch (err) {
      console.error('Failed to start solver', err);
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
      if (data.status === 'ai_won') {
        setStatus('solved');
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
      if (data.status === 'ai_won') {
        setStatus('solved');
      }
      await fetchAiState(id);
    } catch {
      /* tick failure — retry on next interval */
    }
  }, [fetchAiState]);

  // GA tick polling
  useEffect(() => {
    if (!matchId || status !== 'solving') {
      clearInterval(timerRef.current);
      return;
    }
    timerRef.current = setInterval(() => triggerAiTick(matchId), 1200);
    triggerAiTick(matchId);
    return () => clearInterval(timerRef.current);
  }, [matchId, status, triggerAiTick]);

  // ---- Handlers ----

  const handleCellChange = (idx, val) => {
    const next = [...playerBoard];
    next[idx] = val;
    setPlayerBoard(next);
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
    } finally {
      setLoading(false);
    }
  };

  const onFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (file) await handleUploadImage(file);
    e.target.value = '';
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
      if (status !== 'idle') return;
      handlePaste(e);
    };
    window.addEventListener('paste', onWindowPaste);
    return () => window.removeEventListener('paste', onWindowPaste);
  }, [handlePaste, status]);

  const handleReset = () => {
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

  const uncertainCells =
    showOcrReview && playerBoard.length
      ? playerBoard.map(
          (v, i) => Boolean(v) && (ocrConfidences[i] ?? 0) < OCR_UNCERTAIN_THRESHOLD,
        )
      : [];
  const detectedCount = showOcrReview ? playerBoard.filter((v) => v !== 0).length : 0;
  const uncertainCount = showOcrReview ? uncertainCells.filter(Boolean).length : 0;
  const hasPuzzle = playerBoard.some((c) => c !== 0);

  return (
    <div className="page">
      {status === 'idle' && (
        <div className="start-screen">
          <h2>SUDOKU SOLVER</h2>
          <p>
            Paste a screenshot from sudoku.com (Ctrl+V) or upload an image.
            OCR extracts the puzzle, then a genetic algorithm solves it.
          </p>

          {!hasPuzzle && (
            <div
              className="drop-zone"
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: '3px dashed #000',
                padding: '2rem 3rem',
                cursor: 'pointer',
                textAlign: 'center',
                boxShadow: 'var(--shadow-sm)',
                background: 'var(--bg-secondary)',
                maxWidth: 420,
                width: '100%',
              }}
            >
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📋</div>
              <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>
                PASTE SCREENSHOT (Ctrl+V)
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                or click to upload an image
              </div>
            </div>
          )}

          {hasPuzzle && (
            <div className="boards-container" style={{ gridTemplateColumns: '1fr', maxWidth: 400 }}>
              <PlayerBoard
                board={playerBoard}
                startingBoard={new Array(gridSize * gridSize).fill(0)}
                gridSize={gridSize}
                onChange={handleCellChange}
                disabled={loading}
                uncertainCells={uncertainCells}
              />
            </div>
          )}

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
                CLEAR UNCERTAIN
              </button>
              <button className="btn-secondary" onClick={() => setShowOcrReview(false)} disabled={loading}>
                ACCEPT OCR
              </button>
            </div>
          )}

          <div className="actions-row" style={{ gap: '0.75rem' }}>
            {!hasPuzzle && (
              <>
                <div className="difficulty-picker">
                  {['easy', 'medium', 'hard'].map((d) => (
                    <button
                      key={d}
                      className={`difficulty-btn ${difficulty === d ? 'active' : ''}`}
                      onClick={() => setDifficulty(d)}
                    >
                      {d.toUpperCase()}
                    </button>
                  ))}
                </div>
                <button
                  className="btn-primary"
                  onClick={startSolving}
                  disabled={loading}
                  id="start-match-btn"
                >
                  {loading ? 'GENERATING...' : 'GENERATE & SOLVE'}
                </button>
              </>
            )}
            {hasPuzzle && (
              <>
                <button
                  className="btn-primary"
                  onClick={startSolving}
                  disabled={loading}
                  id="start-match-btn"
                >
                  {loading ? 'STARTING...' : 'SOLVE WITH GA →'}
                </button>
                <button className="btn-secondary" onClick={handleReset} disabled={loading}>
                  CLEAR
                </button>
              </>
            )}
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

      {(status === 'solving' || status === 'solved') && (
        <>
          <SudokuHUD generation={generation} fitness={fitness} status={status} />

          <div className="boards-container" style={{ gridTemplateColumns: '1fr', maxWidth: 480 }}>
            <AiBoard
              bestBoard={bestBoard}
              startingBoard={startingBoard}
              heatmapData={heatmap}
              gridSize={gridSize}
            />
          </div>

          {status === 'solved' && (
            <div style={{
              border: '3px solid #000',
              background: '#000',
              color: 'var(--success)',
              padding: '1rem 2rem',
              fontWeight: 700,
              fontSize: '1.25rem',
              boxShadow: 'var(--shadow)',
              textAlign: 'center',
            }}>
              SOLVED IN {generation} GENERATIONS
            </div>
          )}

          <div className="actions-row">
            <button className="btn-secondary" onClick={handleReset}>
              ← NEW PUZZLE
            </button>
          </div>
        </>
      )}
    </div>
  );
}
