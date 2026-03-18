# Sudoku Solver — Verification Plan

## Purpose

Sign-off and repeatable checks before merge and for future regression.

## Prerequisites

- `docker compose up -d`; backend and frontend-sudoku services healthy.

## Verification steps

1. Ensure Docker Compose is running; open UI at http://localhost/sudoku/
2. Enter numbers on the board (or leave default), click **Solve with GA** → evolution runs, heatmap updates in browser.
3. Paste an image of a Sudoku puzzle → OCR endpoint is invoked, board populates.

## Success criteria

- All steps pass.
- **Solve with GA** updates the board and heatmap.
- Image paste populates the board.

## Notes

- API base: `/api/v1/sudoku`.
- Backend uses OpenCV/Tesseract (configured in Dockerfile).
