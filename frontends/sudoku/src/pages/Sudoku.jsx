import { useState, useEffect, useRef, useCallback } from 'react';
import AiBoard from '../components/AiBoard.jsx';
import SudokuHUD from '../components/SudokuHUD.jsx';
import PlayerBoard from '../components/PlayerBoard.jsx';
import { parsePastedBoard } from '../utils/sudokuOcr.js';

const API = '/api/v1/sudoku';
const OCR_UNCERTAIN_THRESHOLD = 0.6;
const POLL_INTERVAL_MS = 500;

export default function Sudoku() {
  const [matchId, setMatchId] = useState(null);
  const [startingBoard, setStartingBoard] = useState([]);
  const [inputBoard, setInputBoard] = useState([]);
  const [ocrConfidences, setOcrConfidences] = useState([]);
  const [showOcrReview, setShowOcrReview] = useState(false);
  const [gridSize, setGridSize] = useState(9);
  const [status, setStatus] = useState('idle'); // idle | loading | solving | solved
  const [error, setError] = useState(null);
  const [dragging, setDragging] = useState(false);

  // Solver state
  const [generation, setGeneration] = useState(0);
  const [fitness, setFitness] = useState(0);
  const [heatmap, setHeatmap] = useState([]);
  const [bestBoard, setBestBoard] = useState([]);

  const pollRef = useRef(null);
  const fileInputRef = useRef(null);

  // ---- Solve flow: create match → POST /solve → poll until solved ----

  const startSolving = async () => {
    setStatus('loading');
    setError(null);
    try {
      const custom_board =
        inputBoard?.length === gridSize * gridSize && inputBoard.some((c) => c !== 0)
          ? inputBoard
          : null;

      // 1. Create match
      const res = await fetch(`${API}/matches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ difficulty: 'medium', grid_size: gridSize, custom_board }),
      });
      const data = await res.json();
      const newMatchId = data.match_id;

      setMatchId(newMatchId);
      setStartingBoard(data.starting_board);
      setGridSize?.(data.grid_size);
      setGeneration(0);
      setFitness(0);
      setHeatmap([]);
      setBestBoard([...data.starting_board]);
      setShowOcrReview(false);
      setStatus('solving');

      // 2. Queue distributed solve
      await fetch(`${API}/matches/${newMatchId}/solve`, { method: 'POST' });

      // 3. Start fast polling
      startPolling(newMatchId);
    } catch (err) {
      setError(`Failed to start solver: ${err.message || err}`);
      setStatus('idle');
    }
  };

  const startPolling = useCallback((id) => {
    if (pollRef.current) clearInterval(pollRef.current);

    const poll = async () => {
      try {
        const res = await fetch(`${API}/matches/${id}`);
        const data = await res.json();
        setGeneration(data.ai.generation_count);
        setFitness(data.ai.fitness_score);
        if (data.ai.heatmap_data?.length) setHeatmap(data.ai.heatmap_data);
        if (data.ai.best_board?.length) setBestBoard(data.ai.best_board);

        if (data.status === 'solved' || data.status === 'ai_won') {
          setStatus('solved');
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
      } catch {
        // polling failure — will retry next interval
      }
    };

    poll(); // immediate first poll
    pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  // ---- OCR ----

  const handleUploadImage = async (file) => {
    if (!file || !file.type?.startsWith('image/')) return;
    setStatus('loading');
    setError(null);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API}/extract-board`, { method: 'POST', body: formData });
      if (!res.ok) throw new Error('OCR failed');
      const data = await res.json();

      setInputBoard(data.board);
      const conf = data.confidences?.map((c) => Math.max(0, Math.min(1, Number(c) || 0))) || [];
      setOcrConfidences(conf);
      setShowOcrReview(true);
      setStatus('idle');
    } catch {
      setError('Failed to extract digits from image. Try a cleaner screenshot.');
      setStatus('idle');
    }
  };

  // ---- Paste / Drop handlers ----

  const handlePaste = useCallback(async (e) => {
    if (status !== 'idle') return;
    const items = e.clipboardData?.items || [];
    for (let i = 0; i < items.length; i++) {
      if (items[i].type?.includes('image')) {
        await handleUploadImage(items[i].getAsFile());
        return;
      }
    }
    const text = e.clipboardData?.getData('text') || '';
    const board = parsePastedBoard(text, gridSize);
    if (board) setInputBoard(board);
  }, [status, gridSize]);

  useEffect(() => {
    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [handlePaste]);

  const handleDrop = async (e) => {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer?.files?.[0];
    if (file) await handleUploadImage(file);
  };

  const handleCellChange = (idx, val) => {
    const next = [...inputBoard];
    next[idx] = val;
    setInputBoard(next);
  };

  const handleReset = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    setMatchId(null);
    setStatus('idle');
    setStartingBoard([]);
    setInputBoard([]);
    setOcrConfidences([]);
    setShowOcrReview(false);
    setGeneration(0);
    setFitness(0);
    setHeatmap([]);
    setBestBoard([]);
    setError(null);
  };

  // ---- Derived state ----

  const uncertainCells = showOcrReview
    ? inputBoard.map((v, i) => Boolean(v) && (ocrConfidences[i] ?? 0) < OCR_UNCERTAIN_THRESHOLD)
    : [];
  const detectedCount = showOcrReview ? inputBoard.filter((v) => v !== 0).length : 0;
  const uncertainCount = uncertainCells.filter(Boolean).length;
  const hasPuzzle = inputBoard.some((c) => c !== 0);
  const isLoading = status === 'loading';

  // ---- Render ----

  return (
    <div className="page">
      {/* ── IDLE: Input puzzle ── */}
      {(status === 'idle' || status === 'loading') && (
        <div className="start-screen">
          <h2>SUDOKU SOLVER</h2>

          {error && (
            <div className="error-banner">{error}</div>
          )}

          {!hasPuzzle ? (
            <div
              className={`drop-zone ${dragging ? 'drop-zone--active' : ''}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
            >
              {isLoading ? (
                <>
                  <div className="drop-zone__icon">⏳</div>
                  <div className="drop-zone__title">EXTRACTING DIGITS...</div>
                </>
              ) : (
                <>
                  <div className="drop-zone__icon">📋</div>
                  <div className="drop-zone__title">PASTE SCREENSHOT (Ctrl+V)</div>
                  <div className="drop-zone__subtitle">or drag & drop / click to upload</div>
                </>
              )}
            </div>
          ) : (
            <div className="puzzle-preview">
              <PlayerBoard
                board={inputBoard}
                startingBoard={new Array(gridSize * gridSize).fill(0)}
                gridSize={gridSize}
                onChange={handleCellChange}
                disabled={isLoading}
                uncertainCells={uncertainCells}
              />
            </div>
          )}

          {showOcrReview && (
            <div className="ocr-review">
              <span className="ocr-review__info">
                Detected <b>{detectedCount}</b> digits
                {uncertainCount > 0 && <>, <b>{uncertainCount}</b> uncertain</>}
              </span>
              <div className="actions-row">
                {uncertainCount > 0 && (
                  <button
                    className="btn-secondary"
                    onClick={() => setInputBoard(inputBoard.map((v, i) => (uncertainCells[i] ? 0 : v)))}
                  >
                    CLEAR UNCERTAIN
                  </button>
                )}
                <button className="btn-secondary" onClick={() => setShowOcrReview(false)}>
                  LOOKS GOOD
                </button>
              </div>
            </div>
          )}

          <div className="actions-row">
            {hasPuzzle ? (
              <>
                <button className="btn-primary" onClick={startSolving} disabled={isLoading} id="start-match-btn">
                  {isLoading ? 'STARTING...' : 'SOLVE →'}
                </button>
                <button className="btn-secondary" onClick={handleReset} disabled={isLoading}>
                  CLEAR
                </button>
              </>
            ) : (
              <button className="btn-primary" onClick={startSolving} disabled={isLoading} id="start-match-btn">
                {isLoading ? 'GENERATING...' : 'GENERATE RANDOM PUZZLE'}
              </button>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={async (e) => { if (e.target.files?.[0]) await handleUploadImage(e.target.files[0]); e.target.value = ''; }}
          />
        </div>
      )}

      {/* ── SOLVING / SOLVED ── */}
      {(status === 'solving' || status === 'solved') && (
        <div className="solve-screen">
          <SudokuHUD generation={generation} fitness={fitness} status={status} />

          <div className="solve-board">
            <AiBoard
              bestBoard={bestBoard}
              startingBoard={startingBoard}
              heatmapData={heatmap}
              gridSize={gridSize}
            />
          </div>

          {status === 'solved' && (
            <div className="solved-banner">
              SOLVED IN {generation} GENERATIONS
            </div>
          )}

          <div className="actions-row">
            <button className="btn-primary" onClick={handleReset}>
              ← NEW PUZZLE
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
