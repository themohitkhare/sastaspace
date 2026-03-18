# Sudoku Solver — Verification Plan

## Purpose

Sign-off and repeatable checks before merge and for future regression.

## Prerequisites

- `docker compose up -d`; backend and frontend-sudoku services healthy.
- UI available at `http://localhost/sudoku/`.

## Verification steps

### API contract (OCR)

1. Upload an image to OCR endpoint:

```bash
curl -sS -X POST http://localhost/api/v1/sudoku/extract-board \
  -F "file=@/path/to/sudoku.png" | head -c 400; echo
```

2. Verify response:
- `board` exists and has length **81**
- `confidences` exists and has length **81**
- `confidences[i]` are numbers in **[0, 1]**

### UI flow (OCR review → solve)

1. Open UI at `http://localhost/sudoku/`.
2. Paste an image of a Sudoku puzzle (or click **Upload image**).
3. Verify:
   - Board populates with digits.
   - Low-confidence digits are highlighted.
   - **Clear uncertain** clears highlighted digits.
   - **Accept OCR** hides the OCR review banner without changing the board.
4. Fix any remaining digits manually.
5. Click **Start Race**:
   - Backend uses `custom_board` when provided.
   - AI tick polling runs; HUD updates.

## Success criteria

- OCR endpoint returns `board` + `confidences` arrays of length 81.
- UI supports paste/upload OCR, highlights uncertain digits, and lets the user correct quickly.
- Starting a match with a custom board works and the solver runs.

## Notes

- API base: `/api/v1/sudoku`.
- Backend OCR uses OpenCV/Tesseract (configured in `backend/Dockerfile`).

