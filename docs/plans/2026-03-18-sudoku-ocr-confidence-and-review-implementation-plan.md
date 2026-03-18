# Sudoku OCR Confidence + Review UX Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve Sudoku OCR accuracy on grid screenshots and add an OCR Review step so users can quickly correct uncertain cells before solving.

**Architecture:** Keep OCR on the backend (OpenCV + Tesseract), but return per-cell confidence so the frontend can highlight uncertain cells and offer quick correction controls. Preserve backwards compatibility by keeping `board` intact and treating missing `confidences` as best-effort defaults.

**Tech Stack:** FastAPI, Pydantic, OpenCV (`opencv-python`), Tesseract (`pytesseract`), React (Vite).

---

### Task 1: Add OCR confidence to API contract (tests first)

**Files:**
- Modify: `backend/app/modules/sudoku/schemas.py`
- Modify: `backend/app/modules/sudoku/router.py`
- Test: `backend/tests/modules/sudoku/test_api.py`

**Step 1: Write the failing test**

Add a test that uploads an image to `/api/v1/sudoku/extract-board` and asserts:
- Response JSON contains `board` length 81
- Response JSON contains `confidences` length 81
- All confidences are numbers in \([0, 1]\)

Example skeleton:

```python
def test_extract_board_includes_confidences(client):
    with open("tests/fixtures/sudoku/grid.png", "rb") as f:
        res = client.post("/api/v1/sudoku/extract-board", files={"file": ("grid.png", f, "image/png")})
    assert res.status_code == 200
    data = res.json()
    assert len(data["board"]) == 81
    assert len(data["confidences"]) == 81
    assert all(isinstance(c, (int, float)) for c in data["confidences"])
    assert all(0.0 <= float(c) <= 1.0 for c in data["confidences"])
```

**Step 2: Run test to verify it fails**

Run (inside container, since local `pytest` may not be installed):

```bash
docker exec -t sastaspace-backend python -m pytest -q /app/tests/modules/sudoku/test_api.py -k confidences
```

Expected: FAIL with `KeyError: 'confidences'` (or schema mismatch).

**Step 3: Minimal implementation**

- Update `ExtractBoardResponse` in `backend/app/modules/sudoku/schemas.py`:

```python
class ExtractBoardResponse(BaseModel):
    board: list[int]
    confidences: list[float]
```

- Update `backend/app/modules/sudoku/router.py` `extract_board()` to return confidences (placeholder values initially to make test pass, e.g. `1.0` for non-zero digits, `0.0` for zeros).

**Step 4: Run test to verify it passes**

```bash
docker exec -t sastaspace-backend python -m pytest -q /app/tests/modules/sudoku/test_api.py -k confidences
```

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/modules/sudoku/schemas.py backend/app/modules/sudoku/router.py backend/tests/modules/sudoku/test_api.py
git commit -m "$(cat <<'EOF'
feat(sudoku): return OCR confidences from extract-board

Expose per-cell OCR confidence alongside the extracted board to enable UI review of uncertain cells.
EOF
)"
```

---

### Task 2: Improve OCR pipeline (digit isolation + real confidence)

**Files:**
- Modify: `backend/app/modules/sudoku/ocr_utils.py`
- Modify: `backend/app/modules/sudoku/router.py`
- Test: `backend/tests/modules/sudoku/test_api.py` (extend assertions)

**Step 1: Write a failing/strengthened test**

Extend the test to assert confidences are not all identical and reflect extracted digits:
- If `board[i] != 0`, then `confidences[i] >= 0.3` (tunable threshold)
- If `board[i] == 0`, then `confidences[i] <= 0.7` (avoid false certainty)

Keep thresholds loose to prevent flakiness.

**Step 2: Run test to verify it fails**

```bash
docker exec -t sastaspace-backend python -m pytest -q /app/tests/modules/sudoku/test_api.py -k confidences
```

Expected: FAIL because placeholder confidence logic doesn’t satisfy the strengthened expectations.

**Step 3: Implement improved OCR with confidence**

In `backend/app/modules/sudoku/ocr_utils.py`:
- Change API to return `(board, confidences)`:

```python
def extract_sudoku_board(image_bytes: bytes) -> tuple[list[int], list[float]]:
    ...
    return board, confidences
```

Per-cell improvements:
- **Grid-line suppression** (morphological line masks):
  - Use `cv2.getStructuringElement` with long kernels to detect horizontal/vertical lines.
  - Subtract/erase those from the binary cell image.
- **Digit contour crop**:
  - Find contours on cleaned binary.
  - Pick candidate by area/aspect ratio and closeness to center.
  - Crop bounding box; pad to square.
- **Normalize**:
  - Resize to fixed size (e.g. 56×56) with padding.
  - Invert to black-on-white for OCR.
- **Confidence**:
  - Use `pytesseract.image_to_data(roi, config=..., output_type=pytesseract.Output.DICT)`
  - Select best recognized digit 1..9; take its confidence \([-1..100]\) → normalize to 0..1.
  - If no valid digit: digit = 0, confidence = 0.0 (or very low).

Update `backend/app/modules/sudoku/router.py` to use the new return type:

```python
board, confidences = extract_sudoku_board(content)
return ExtractBoardResponse(board=board, confidences=confidences)
```

**Step 4: Run tests**

```bash
docker exec -t sastaspace-backend python -m pytest -q /app/tests/modules/sudoku/test_api.py
```

Expected: PASS.

**Step 5: Manual verification (non-test)**

Use your known screenshot:

```bash
curl -sS -X POST http://localhost/api/v1/sudoku/extract-board -F "file=@/path/to/screenshot.png" | head -c 400; echo
```

Confirm `confidences` exists and has 81 floats.

**Step 6: Commit**

```bash
git add backend/app/modules/sudoku/ocr_utils.py backend/app/modules/sudoku/router.py backend/tests/modules/sudoku/test_api.py
git commit -m "$(cat <<'EOF'
feat(sudoku): improve OCR digit isolation and confidence scoring

Enhance preprocessing to suppress grid lines and crop digits before OCR, and return normalized per-cell confidences.
EOF
)"
```

---

### Task 3: Frontend OCR Review UX (highlight + quick correction)

**Files:**
- Modify: `frontends/sudoku/src/pages/Sudoku.jsx`
- Modify: `frontends/sudoku/src/components/UnifiedBoard.jsx` (if needed to support highlighting)
- Modify: `frontends/sudoku/src/index.css` (add highlight styles)
- Test: `frontends/sudoku/src/components/PlayerBoard.test.jsx` or add new test covering highlight rendering (optional but preferred)

**Step 1: Add failing frontend test (preferred)**

If there’s an existing board component test harness, add a test verifying that when a `confidences` array is provided, cells below threshold render with a CSS class (e.g. `.ocr-uncertain`).

Run:

```bash
cd frontends/sudoku && npm test
```

Expected: FAIL before implementation.

**Step 2: Implement OCR Review state in `Sudoku.jsx`**

Add state:
- `ocrConfidences` (length 81)
- `ocrMode` (boolean) or `ocrSummary` (counts)
- threshold const, e.g. `const OCR_UNCERTAIN = 0.6`

On OCR response:
- set `customBoard` from `board`
- set `ocrConfidences` from `confidences` (fallback logic if missing)
- show UI controls:
  - “Clear uncertain” → set cells with confidence < threshold to 0
  - “Accept OCR” → dismiss review UI (keep board)

**Step 3: Wire highlighting into board**

Option A (preferred): pass `confidences` + threshold into `UnifiedBoard` and add a class per cell when confidence is low.

Option B: compute a `Set` of uncertain indices in `Sudoku.jsx` and pass `uncertainCells` down.

**Step 4: Run frontend tests/build**

```bash
cd frontends/sudoku && npm test
cd frontends/sudoku && npm run build
```

Expected: PASS.

**Step 5: Rebuild container and manual verify**

```bash
cd /Users/mkhare/Development/sastaspace
docker compose up -d --build frontend-sudoku
open http://localhost/sudoku/
```

Paste/upload screenshot → digits populate → uncertain cells highlighted → Clear uncertain works → Solve works.

**Step 6: Commit**

```bash
git add frontends/sudoku/src/pages/Sudoku.jsx frontends/sudoku/src/components/UnifiedBoard.jsx frontends/sudoku/src/index.css frontends/sudoku/src/components/PlayerBoard.test.jsx
git commit -m "$(cat <<'EOF'
feat(sudoku): add OCR review and highlight uncertain cells

Display OCR confidence-driven highlights and provide quick correction actions before starting the solver.
EOF
)"
```

---

### Task 4: Update verification docs

**Files:**
- Modify: `docs/plans/2025-03-18-sudoku-solver-verification-design.md`

**Step 1: Update verification steps**

Add explicit checks for:
- `confidences` present in OCR response
- uncertain highlight appears and correction controls function

**Step 2: Commit**

```bash
git add docs/plans/2025-03-18-sudoku-solver-verification-design.md
git commit -m "$(cat <<'EOF'
docs(sudoku): expand OCR verification to include confidence + review UX

EOF
)"
```

---

### Task 5: End-to-end smoke verification

**Files:**
- (no code changes)

**Step 1: Bring stack up**

```bash
cd /Users/mkhare/Development/sastaspace
docker compose up -d --build
```

**Step 2: API smoke**

```bash
curl -sS http://localhost/api/v1/common/health
curl -sS -X POST http://localhost/api/v1/sudoku/matches -H 'Content-Type: application/json' -d '{"difficulty":"medium","grid_size":9,"custom_board":null}'
curl -sS -X POST http://localhost/api/v1/sudoku/extract-board -F "file=@/path/to/grid.png" | head -c 300; echo
```

Expected: 200 health, match created, OCR returns `board` + `confidences`.

**Step 3: UI smoke**

Open `http://localhost/sudoku/`:
- Upload/paste → OCR fills grid
- Uncertain highlights visible
- Clear uncertain works
- Solve starts and AI ticks (HUD increments)

---

Plan complete and saved to `docs/plans/2026-03-18-sudoku-ocr-confidence-and-review-implementation-plan.md`.

Two execution options:

**1. Subagent-Driven (this session)** — I dispatch a fresh agent per task, review between tasks, fast iteration.  
**2. Parallel Session (separate)** — You open a new session in an isolated worktree and we run `superpowers:executing-plans` straight through with checkpoints.

Which approach?

