"""OCR Utilities to parse uploaded Sudoku images (optimized for sudoku.com screenshots)."""

from __future__ import annotations

import cv2
import numpy as np
import pytesseract  # type: ignore[import-untyped]

MIN_IMAGE_SIDE_PX = 60
WARP_TARGET_SIZE_PX = 900


def normalize_confidence(raw_confidence: float | int) -> float:
    """Normalize Tesseract confidence from [-1, 100] into [0.0, 1.0]."""
    raw = float(raw_confidence)
    if raw <= 0:
        return 0.0
    return min(raw / 100.0, 1.0)


def pick_best_digit_from_tesseract_data(data: dict[str, list[str]]) -> tuple[int, float]:
    """Extract the best single digit (1-9) and confidence from tesseract output."""
    texts: list[str] = data.get("text", []) or []
    confs: list[str] = data.get("conf", []) or []

    best_digit = 0
    best_conf = 0.0

    for i, raw_text in enumerate(texts):
        text = raw_text.strip()
        if not text:
            continue
        ch = text[0]
        if not ch.isdigit():
            continue
        value = int(ch)
        if not (1 <= value <= 9):
            continue

        conf_raw = -1.0
        if i < len(confs):
            try:
                conf_raw = float(confs[i])
            except (TypeError, ValueError):
                conf_raw = -1.0

        conf = normalize_confidence(conf_raw)
        if conf > best_conf:
            best_conf = conf
            best_digit = value

    if best_digit == 0:
        return 0, 0.0
    return best_digit, best_conf


def _find_grid_contour(thresh: np.ndarray) -> np.ndarray | None:
    """Find the largest quadrilateral contour (the sudoku grid)."""
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    for c in contours[:5]:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            return approx
    return None


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order 4 points as [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1).flatten()
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


def _warp_grid(gray: np.ndarray, contour: np.ndarray | None) -> np.ndarray:
    """Perspective-warp the grid to a square image."""
    h, w = gray.shape
    if contour is not None:
        pts = contour.reshape(4, 2).astype(np.float32)
        ordered = _order_points(pts)
    else:
        ordered = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)

    dst = np.array(
        [
            [0, 0],
            [WARP_TARGET_SIZE_PX - 1, 0],
            [WARP_TARGET_SIZE_PX - 1, WARP_TARGET_SIZE_PX - 1],
            [0, WARP_TARGET_SIZE_PX - 1],
        ],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(ordered, dst)
    return cv2.warpPerspective(gray, M, (WARP_TARGET_SIZE_PX, WARP_TARGET_SIZE_PX))


def _cell_has_digit(cell_thresh: np.ndarray) -> bool:
    """Check if a thresholded cell contains enough foreground pixels to be a digit."""
    total = cell_thresh.shape[0] * cell_thresh.shape[1]
    fg = cv2.countNonZero(cell_thresh)
    ratio = fg / total if total > 0 else 0
    # Digits typically have 3-40% fill ratio in the center crop
    return 0.01 < ratio < 0.5


def extract_sudoku_board(image_bytes: bytes) -> tuple[list[int], list[float]]:
    """
    OCR a 9x9 Sudoku grid image (optimized for sudoku.com screenshots).

    Returns:
      - board: 81-length list of ints (0 = empty)
      - confidences: 81-length list of floats in [0, 1]
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h_img, w_img = gray.shape
    if min(h_img, w_img) < MIN_IMAGE_SIDE_PX:
        raise ValueError("Image too small for Sudoku OCR.")

    # Find grid and warp
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    thresh_for_contour = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )
    grid_contour = _find_grid_contour(thresh_for_contour)
    warped = _warp_grid(gray, grid_contour)

    # Apply clean threshold to warped image
    warped_blur = cv2.GaussianBlur(warped, (3, 3), 0)
    _, warped_thresh = cv2.threshold(warped_blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    cell_size = WARP_TARGET_SIZE_PX // 9
    board: list[int] = []
    confidences: list[float] = []

    for row in range(9):
        for col in range(9):
            x = col * cell_size
            y = row * cell_size

            # Crop cell with margin to exclude grid lines
            margin = int(cell_size * 0.15)
            cell_gray = warped[
                y + margin : y + cell_size - margin, x + margin : x + cell_size - margin
            ]
            cell_thresh = warped_thresh[
                y + margin : y + cell_size - margin, x + margin : x + cell_size - margin
            ]

            if cell_gray.size == 0 or cell_thresh.size == 0:
                board.append(0)
                confidences.append(0.0)
                continue

            if not _cell_has_digit(cell_thresh):
                board.append(0)
                confidences.append(0.0)
                continue

            # Prepare cell for OCR: resize to consistent size, add padding
            target = 80
            resized = cv2.resize(cell_gray, (target, target), interpolation=cv2.INTER_CUBIC)

            # Add white border padding for tesseract (it needs whitespace around digits)
            pad = 20
            padded = cv2.copyMakeBorder(resized, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=255)

            # Use tesseract with single character mode
            config = "--psm 10 --oem 3 -c tessedit_char_whitelist=123456789"
            data = pytesseract.image_to_data(
                padded,
                config=config,
                output_type=pytesseract.Output.DICT,
            )
            digit, conf = pick_best_digit_from_tesseract_data(data)

            # If PSM 10 failed, try PSM 13 (raw line) as fallback
            if digit == 0:
                config_fallback = "--psm 13 --oem 3 -c tessedit_char_whitelist=123456789"
                text = pytesseract.image_to_string(padded, config=config_fallback).strip()
                if text and text[0].isdigit():
                    val = int(text[0])
                    if 1 <= val <= 9:
                        digit = val
                        conf = 0.5  # lower confidence for fallback

            board.append(digit)
            confidences.append(conf)

    if len(board) != 81 or len(confidences) != 81:
        raise ValueError("OCR extracted an unexpected number of cells.")

    return board, confidences
