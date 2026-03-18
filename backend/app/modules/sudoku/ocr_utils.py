"""OCR Utilities to parse uploaded Sudoku images."""

from __future__ import annotations

import cv2
import numpy as np
import pytesseract  # type: ignore[import-untyped]

MIN_IMAGE_SIDE_PX = 60
MIN_CELL_SIZE_PX = 8
OCR_TARGET_SIZE_PX = 56
MIN_DIGIT_FG_RATIO = 0.006
WARP_TARGET_SIZE_PX = 900


def normalize_confidence(raw_confidence: float | int) -> float:
    """
    Normalize a Tesseract confidence value from [-1, 100] into [0.0, 1.0].
    Values at or below 0 are treated as 0.0; values above 100 are clamped.
    """
    raw = float(raw_confidence)
    if raw <= 0:
        return 0.0
    normalized = raw / 100.0
    if normalized < 0.0:
        return 0.0
    if normalized > 1.0:
        return 1.0
    return normalized


def pick_best_digit_from_tesseract_data(data: dict[str, list[str]]) -> tuple[int, float]:
    """
    Extract the best single digit (1..9) and its normalized confidence from
    pytesseract.image_to_data(..., output_type=DICT).

    Returns (0, 0.0) when no valid digit is present.
    """
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


def extract_sudoku_board(image_bytes: bytes) -> tuple[list[int], list[float]]:
    """
    Best-effort OCR for a 9x9 Sudoku grid image.

    Returns:
      - board: 81-length list of ints (0 = empty)
      - confidences: 81-length list of floats in [0, 1]

    Note: This is the baseline OCR implementation. Follow-up work will improve
    digit isolation and confidence scoring.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h_img, w_img = gray.shape
    if min(h_img, w_img) < MIN_IMAGE_SIDE_PX:
        raise ValueError("Image too small for Sudoku OCR.")
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No grid found in image.")

    contours = sorted(contours, key=cv2.contourArea, reverse=True)
    puzzle_contour = None
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            puzzle_contour = approx
            break

    if puzzle_contour is None:
        h, w = gray.shape
        puzzle_contour = np.array([[[0, 0]], [[w - 1, 0]], [[w - 1, h - 1]], [[0, h - 1]]])

    pts = puzzle_contour.reshape(4, 2)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]

    src_pts = np.array([tl, tr, br, bl], dtype=np.float32)
    side_candidates = [
        float(np.linalg.norm(br - bl)),
        float(np.linalg.norm(tr - tl)),
        float(np.linalg.norm(br - tr)),
        float(np.linalg.norm(bl - tl)),
    ]
    side = max(side_candidates)
    dst_pts = np.array(
        [[0, 0], [side - 1, 0], [side - 1, side - 1], [0, side - 1]],
        dtype=np.float32,
    )
    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped_size = int(max(side, 1.0))
    warped = cv2.warpPerspective(gray, M, (warped_size, warped_size))
    if warped_size < WARP_TARGET_SIZE_PX:
        warped = cv2.resize(warped, (WARP_TARGET_SIZE_PX, WARP_TARGET_SIZE_PX))
        warped_size = WARP_TARGET_SIZE_PX

    board: list[int] = []
    confidences: list[float] = []
    cell_size = max(int(warped_size / 9), 1)

    # Reject images that would produce essentially meaningless cells.
    if warped_size < 9 * MIN_CELL_SIZE_PX or cell_size < MIN_CELL_SIZE_PX:
        raise ValueError("Computed cell size is too small for Sudoku OCR.")

    for row in range(9):
        for col in range(9):
            x = col * cell_size
            y = row * cell_size
            cell = warped[y : y + cell_size, x : x + cell_size]

            margin = int(cell_size * 0.1)
            if margin > 0:
                cell = cell[margin : cell_size - margin, margin : cell_size - margin]

            if cell.size == 0:
                board.append(0)
                confidences.append(0.0)
                continue

            cell_thresh = cv2.adaptiveThreshold(
                cell, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
            )
            kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            cell_thresh = cv2.morphologyEx(cell_thresh, cv2.MORPH_OPEN, kernel_small)

            # Remove horizontal and vertical grid lines using morphology.
            # Use moderately long kernels to detect grid lines, but avoid being
            # so long that we erase legitimate digit strokes.
            horizontal_kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT, (max(cell_thresh.shape[1] // 3, 1), 1)
            )
            vertical_kernel = cv2.getStructuringElement(
                cv2.MORPH_RECT, (1, max(cell_thresh.shape[0] // 3, 1))
            )
            detected_horizontal = cv2.morphologyEx(cell_thresh, cv2.MORPH_OPEN, horizontal_kernel)
            detected_vertical = cv2.morphologyEx(cell_thresh, cv2.MORPH_OPEN, vertical_kernel)
            cell_no_lines = cv2.subtract(
                cv2.subtract(cell_thresh, detected_horizontal), detected_vertical
            )

            # Thin/anti-aliased digits can have very few foreground pixels; keep
            # this threshold low to avoid false-empties.
            if cv2.countNonZero(cell_no_lines) < (
                cell_no_lines.shape[0] * cell_no_lines.shape[1] * MIN_DIGIT_FG_RATIO
            ):
                board.append(0)
                confidences.append(0.0)
                continue

            # Lightly dilate to strengthen digit strokes after line removal.
            cell_no_lines = cv2.dilate(cell_no_lines, kernel_small, iterations=2)

            # Find the main digit contour and crop tightly.
            contours_cell, _ = cv2.findContours(
                cell_no_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours_cell:
                board.append(0)
                confidences.append(0.0)
                continue

            contour = max(contours_cell, key=cv2.contourArea)
            x_c, y_c, w_c, h_c = cv2.boundingRect(contour)

            if w_c <= 0 or h_c <= 0:
                board.append(0)
                confidences.append(0.0)
                continue

            side_c = max(w_c, h_c)
            cx = x_c + w_c // 2
            cy = y_c + h_c // 2
            half_side = side_c // 2
            x_start = max(cx - half_side, 0)
            y_start = max(cy - half_side, 0)
            x_end = min(x_start + side_c, cell_no_lines.shape[1])
            y_end = min(y_start + side_c, cell_no_lines.shape[0])

            digit_roi = cell_no_lines[y_start:y_end, x_start:x_end]
            if digit_roi.size == 0:
                board.append(0)
                confidences.append(0.0)
                continue

            # Normalize ROI to a fixed size for OCR.
            digit_roi = cv2.resize(digit_roi, (OCR_TARGET_SIZE_PX, OCR_TARGET_SIZE_PX))
            digit_roi_inv = cv2.bitwise_not(digit_roi)

            config = "--psm 10 --oem 3 -c tessedit_char_whitelist=123456789"
            data = pytesseract.image_to_data(
                digit_roi_inv,
                config=config,
                output_type=pytesseract.Output.DICT,
            )
            digit, conf = pick_best_digit_from_tesseract_data(data)
            board.append(digit)
            confidences.append(conf)

    if len(board) != 81 or len(confidences) != 81:
        raise ValueError("OCR extracted an unexpected number of cells.")

    # Final clamp to ensure all confidences are within [0.0, 1.0].
    confidences = [normalize_confidence(c) for c in confidences]

    return board, confidences
