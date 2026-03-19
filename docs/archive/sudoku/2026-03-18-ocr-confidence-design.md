# Sudoku OCR — Confidence + Review UX (Design)

## Background

Sudoku OCR currently uses OpenCV preprocessing and per-cell Tesseract OCR (`backend/app/modules/sudoku/ocr_utils.py`). The frontend (`frontends/sudoku/src/pages/Sudoku.jsx`) supports paste/upload and fills the grid from `POST /api/v1/sudoku/extract-board`.

## Problem

On screenshots from sources like [Sudoku.com Extreme](https://sudoku.com/extreme/), OCR detects **only a subset** of digits. Users can’t reliably start solving from an image without manual cleanup.

Root causes (observed/expected):
- Digits are thin/anti-aliased and compete with grid lines.
- Current pipeline classifies many cells as “empty” due to simplistic non-zero thresholding.
- Tesseract performance depends heavily on digit isolation, scale, and contrast normalization.

## Questions and Answers

- **Q: Should OCR be purely automatic or allow user correction?**  
  **A:** Automatic extraction should be “best effort”, but the UI must provide a fast correction loop (review step) before solving.

- **Q: Should this be backend or frontend OCR?**  
  **A:** Backend remains the source of truth (existing OpenCV/Tesseract stack), frontend focuses on UX and review.

- **Q: How do we measure “OCR quality”?**  
  **A:** Return per-cell confidence and highlight uncertain cells; success is “most digits correct automatically + quick manual correction for the rest.”

## Design

### API Contract

**Endpoint:** `POST /api/v1/sudoku/extract-board`  
**Request:** `multipart/form-data` with `file` (image)  
**Response (new):**
- `board: list[int]` length 81 (0 means empty)
- `confidences: list[float]` length 81, normalized 0..1 (higher = more confident)
- `source: str | None` (optional, e.g. `"tesseract"`)
- `debug: object | None` (optional, gated by env/flag; includes intermediate crop info)

Backward compatibility:
- Keep `board` as-is.
- If `confidences` missing, frontend assumes `1.0` for non-zero and `0.0` for zero.

### Backend OCR Pipeline Changes

Replace the current “threshold + tesseract” per-cell approach with a more robust per-cell digit isolation:

Per cell, run:
1. **Border margin crop** (keep; may tune).
2. **Grid-line suppression**:
   - Use morphological operations to isolate/remove long horizontal/vertical lines.
   - Subtract line mask from the cell image before digit extraction.
3. **Digit contour extraction**:
   - Find connected components / contours on the cleaned binary image.
   - Choose the best digit candidate by heuristics (area range, aspect ratio, centeredness).
   - Crop tightly around the digit bounding box.
4. **Normalize for OCR**:
   - Resize to a fixed size (e.g. 28×28 or 56×56) with padding.
   - Contrast normalization / denoise.
5. **OCR + confidence**:
   - Use `pytesseract.image_to_data(..., output_type=DICT)` to get per-symbol confidences.
   - Confidence for a cell is the selected symbol’s confidence mapped into 0..1.
   - If OCR yields no valid 1..9, return `0` with low confidence.

### Frontend UX Changes (OCR Review)

Add an OCR Review step after paste/upload:
- **Autofill**: set `customBoard` from `board`.
- **Confidence-aware highlighting**:
  - Cells with confidence below a threshold (e.g. `< 0.6`) get a visible highlight.
  - Provide a small panel: “OCR detected X digits, Y uncertain”.
- **Fast correction loop**:
  - User can click highlighted cells and type the digit.
  - Provide “Accept OCR” (proceed) and “Clear uncertain” (set low-confidence cells back to 0).
- **Solve**:
  - `Solve with GA` uses `customBoard` as `custom_board` for `POST /matches`.

## Implementation Plan (high-level)

Backend:
- Update `ExtractBoardResponse` schema to include `confidences` (+ optional metadata).
- Implement improved OCR pipeline and confidence extraction.
- Add lightweight regression tests around response shape and confidence length.

Frontend:
- Consume `confidences` and highlight low-confidence cells.
- Add small OCR Review controls (accept/clear uncertain).

## Examples

### ✅ Good

- Paste a grid screenshot → board populates → uncertain cells highlighted → user fixes 2–5 cells → click Solve → GA runs.

### ❌ Bad

- Paste a screenshot → partial digits appear with no indication what’s missing → user doesn’t know what to correct → Solve starts with wrong givens.

## Trade-offs

- **Pros**: Much better usability without requiring perfect OCR; measurable confidence; minimal new dependencies.
- **Cons**: OCR still heuristic-based; confidence is “best available” from Tesseract and may not perfectly reflect correctness; added UI complexity.

