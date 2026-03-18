import { useState, useEffect, useRef, useCallback } from 'react';
import UnifiedBoard from '../components/UnifiedBoard.jsx';
import SudokuHUD from '../components/SudokuHUD.jsx';
import EndGameModal from '../components/EndGameModal.jsx';
import { useParams, useNavigate } from 'react-router-dom';
import { parsePastedBoard } from '../utils/sudokuOcr.js';

const API = '/api/v1/sudoku';

export default function Sudoku() {
  const { matchId: urlMatchId } = useParams();
  const navigate = useNavigate();

  const [matchId, setMatchId] = useState(urlMatchId || null);
  const [customBoard, setCustomBoard] = useState(new Array(81).fill(0));
  const [startingBoard, setStartingBoard] = useState([]);
  const [gridSize, setGridSize] = useState(9);
  const [difficulty, setDifficulty] = useState('medium');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [status, setStatus] = useState('idle');
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef(null);

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
        body: JSON.stringify({ 
           difficulty, 
           custom_board: customBoard.some(c => c !== 0) ? customBoard : null 
        }),
      });
      const data = await res.json();
      setMatchId(data.match_id);
      navigate(`/${data.match_id}`);
      setStartingBoard(data.starting_board);
      setCustomBoard([...data.starting_board]); // Lock original input
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
      if (!res.ok) {
        if (res.status === 404) {
          navigate('/');
        }
        return;
      }
      const data = await res.json();
      setGeneration(data.ai.generation_count);
      setFitness(data.ai.fitness_score);
      setHeatmap(data.ai.heatmap_data);
      setBestBoard(data.ai.best_board);

      if (startingBoard.length === 0) {
          setStartingBoard(data.starting_board);
          setCustomBoard(data.starting_board);
          setStatus(data.status);
          setGridSize(data.grid_size || 9);
      } else if (data.status !== 'in_progress') {
        setStatus(data.status);
      }
    } catch {
      /* polling failure — ignore */
    }
  }, [navigate, startingBoard.length]);

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

  // Initialize from URL param if present
  useEffect(() => {
    if (urlMatchId && status === 'idle' && startingBoard.length === 0) {
        setMatchId(urlMatchId);
        setStatus('in_progress');
        fetchAiState(urlMatchId);
    }
  }, [urlMatchId, status, startingBoard.length, fetchAiState]);

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
    if (status !== 'idle') return; // Read-only while solving
    const next = [...customBoard];
    next[idx] = val;
    setCustomBoard(next);
  };

  const handlePaste = async (e) => {
    if (status !== 'idle') return;
    
    const items = e.clipboardData.items;
    let imageFile = null;
    
    for (let i = 0; i < items.length; i++) {
        if (items[i].type.indexOf('image') !== -1) {
            imageFile = items[i].getAsFile();
            break;
        }
    }

    if (imageFile) {
        setLoading(true);
        try {
            const formData = new FormData();
            formData.append('file', imageFile);
            
            const res = await fetch(`${API}/extract-board`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if (data.board) {
                setCustomBoard(data.board);
            }
        } catch (err) {
            console.error('OCR paste failed:', err);
            alert("Failed to extract Sudoku board from image.");
        } finally {
            setLoading(false);
        }
        return;
    }

    // Fallback to basic text parsing
    const text = e.clipboardData.getData('text');
    const board = parsePastedBoard(text, gridSize);
    if (board) {
      setCustomBoard(board);
    }
  };

  const handleUploadImage = async (file) => {
    if (status !== 'idle') return;
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
      if (data.board) {
        setCustomBoard(data.board);
      }
    } catch (err) {
      console.error('OCR upload failed:', err);
      alert('Failed to extract Sudoku board from image.');
    } finally {
      setLoading(false);
    }
  };

  const onFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (file) await handleUploadImage(file);
    // allow re-uploading same file
    e.target.value = '';
  };

  // Capture paste anywhere on the page (paste is flaky if focus isn't on the board)
  useEffect(() => {
    const onWindowPaste = (e) => handlePaste(e);
    window.addEventListener('paste', onWindowPaste);
    return () => window.removeEventListener('paste', onWindowPaste);
  }, [handlePaste]);

  const handlePlayAgain = () => {
    navigate('/');
    setMatchId(null);
    setStatus('idle');
    setStartingBoard([]);
    setCustomBoard(new Array(gridSize * gridSize).fill(0));
    setGeneration(0);
    setFitness(0);
    setHeatmap([]);
    setBestBoard([]);
  };

  // ---- Render ----

  const isGameOver = status === 'player_won' || status === 'ai_won';
  const displayBoard = status === 'idle' ? customBoard : bestBoard;
  const boardKeys = status === 'idle' ? customBoard : startingBoard;

  return (
    <div className="page" onPaste={handlePaste}>
      {status === 'idle' && (
        <div className="start-screen">
          <h2>Sudoku Solver</h2>
          <p>
            Paste an image or type numbers to set up your Sudoku puzzle.
            Our Genetic Algorithm will solve it!
          </p>
          <div className="actions-row">
            <button
              className="btn-primary"
              onClick={startMatch}
              disabled={loading}
              id="start-match-btn"
            >
              {loading ? 'Processing…' : 'Solve with GA'}
            </button>
            <button
              className="btn-secondary"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading}
            >
              Upload Image
            </button>
            <button className="btn-secondary" onClick={handlePlayAgain}>
                Clear
            </button>
          </div>

          <div className="advanced-controls">
            <button
              type="button"
              className="btn-secondary btn-advanced-toggle"
              onClick={() => setShowAdvanced((v) => !v)}
              aria-expanded={showAdvanced}
              aria-controls="sudoku-advanced-panel"
              disabled={loading}
            >
              Advanced {showAdvanced ? '▲' : '▼'}
            </button>

            {showAdvanced && (
              <div
                id="sudoku-advanced-panel"
                className="advanced-panel"
                role="region"
                aria-label="Advanced Sudoku controls"
              >
                <div className="advanced-row">
                  <span className="advanced-label">Difficulty</span>
                  <div className="difficulty-picker" aria-label="Difficulty picker">
                    <button
                      type="button"
                      className={`difficulty-btn ${difficulty === 'easy' ? 'active' : ''}`}
                      onClick={() => setDifficulty('easy')}
                      disabled={loading}
                    >
                      Easy
                    </button>
                    <button
                      type="button"
                      className={`difficulty-btn ${difficulty === 'medium' ? 'active' : ''}`}
                      onClick={() => setDifficulty('medium')}
                      disabled={loading}
                    >
                      Medium
                    </button>
                    <button
                      type="button"
                      className={`difficulty-btn ${difficulty === 'hard' ? 'active' : ''}`}
                      onClick={() => setDifficulty('hard')}
                      disabled={loading}
                    >
                      Hard
                    </button>
                  </div>
                </div>
              </div>
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

      {status !== 'idle' && (
        <SudokuHUD generation={generation} fitness={fitness} status={status} />
      )}

      <div className="boards-container single-board-mode">
          <UnifiedBoard
              board={displayBoard}
              startingBoard={boardKeys}
              heatmapData={heatmap}
              gridSize={gridSize}
              status={status}
              onChange={handleCellChange}
          />
      </div>

       {status !== 'idle' && !isGameOver && (
          <div className="actions-row" style={{marginTop: '1.5rem'}}>
              <button className="btn-secondary" onClick={handlePlayAgain}>
                  Stop & Edit
              </button>
          </div>
      )}

      {isGameOver && (
        <EndGameModal status={status} onPlayAgain={handlePlayAgain} />
      )}
    </div>
  );
}
