"""OCR Utilities to parse uploaded Sudoku images."""

import cv2
import numpy as np
import pytesseract  # type: ignore[import-untyped]


def extract_sudoku_board(image_bytes: bytes) -> list[int]:
    """
    Given raw image bytes of a Sudoku puzzle, uses OpenCV and Tesseract
    to extract the digits and return a 81-length list of integers.
    Empty cells are represented as 0.
    """
    # 1. Load image from bytes
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Could not decode image.")

    # 2. Preprocessing for contour detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (5, 5), 0)
    thresh = cv2.adaptiveThreshold(
        blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
    )

    # 3. Find the largest contour, assume it's the Sudoku board
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
        # Fallback: assume the whole image is the board if no clear box is found
        h, w = gray.shape
        puzzle_contour = np.array([[[0, 0]], [[w - 1, 0]], [[w - 1, h - 1]], [[0, h - 1]]])

    # 4. Perspective warp to get a flat top-down square image
    pts = puzzle_contour.reshape(4, 2)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)

    tl = pts[np.argmin(s)]
    br = pts[np.argmax(s)]
    tr = pts[np.argmin(diff)]
    bl = pts[np.argmax(diff)]

    src_pts = np.array([tl, tr, br, bl], dtype=np.float32)

    side = max(
        np.linalg.norm(br - bl),
        np.linalg.norm(tr - tl),
        np.linalg.norm(br - tr),
        np.linalg.norm(bl - tl),
    )

    dst_pts = np.array(
        [
            [0, 0],
            [side - 1, 0],
            [side - 1, side - 1],
            [0, side - 1],
        ],
        dtype=np.float32,
    )

    M = cv2.getPerspectiveTransform(src_pts, dst_pts)
    warped = cv2.warpPerspective(gray, M, (int(side), int(side)))

    # 5. Extract cells and run OCR
    board: list[int] = []
    cell_size = int(side / 9)

    for row in range(9):
        for col in range(9):
            x = col * cell_size
            y = row * cell_size
            cell = warped[y : y + cell_size, x : x + cell_size]

            # Crop a margin from the cell to avoid border lines
            margin = int(cell_size * 0.1)
            cell = cell[margin : cell_size - margin, margin : cell_size - margin]

            # Threshold the cell for OCR
            cell_thresh = cv2.adaptiveThreshold(
                cell, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
            )

            # Filter noise
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            cell_thresh = cv2.morphologyEx(cell_thresh, cv2.MORPH_OPEN, kernel)

            # Check if cell is empty
            if cv2.countNonZero(cell_thresh) < (cell.shape[0] * cell.shape[1] * 0.05):
                board.append(0)
                continue

            # Invert for Tesseract (black text on white background)
            cell_inv = cv2.bitwise_not(cell_thresh)

            # Tesseract OCR
            config = "--psm 10 --oem 3 -c tessedit_char_whitelist=123456789"
            text: str = pytesseract.image_to_string(cell_inv, config=config).strip()

            if text.isdigit() and 1 <= int(text) <= 9:
                board.append(int(text))
            else:
                board.append(0)

    if len(board) != 81:
        raise ValueError(f"Extracted {len(board)} cells instead of 81.")

    return board
