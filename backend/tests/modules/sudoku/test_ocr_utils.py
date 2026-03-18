from __future__ import annotations

import io

import cv2
import numpy as np

from app.modules.sudoku.ocr_utils import (
    extract_sudoku_board,
    normalize_confidence,
    pick_best_digit_from_tesseract_data,
)


def test_normalize_confidence_clamps_and_scales() -> None:
    assert normalize_confidence(-10.0) == 0.0
    assert normalize_confidence(0.0) == 0.0
    assert normalize_confidence(50.0) == 0.5
    assert normalize_confidence(100.0) == 1.0
    assert normalize_confidence(150.0) == 1.0


def test_extract_sudoku_board_rejects_too_small_images() -> None:
    small_img = np.zeros((20, 20), dtype=np.uint8)
    ok, buf = cv2.imencode(".png", small_img)
    assert ok
    image_bytes = io.BytesIO(buf.tobytes()).getvalue()

    try:
        extract_sudoku_board(image_bytes)
    except ValueError as exc:
        assert "too small" in str(exc).lower()
    else:
        raise AssertionError("Expected ValueError for too-small image")


def test_pick_best_digit_from_tesseract_data_selects_highest_confidence() -> None:
    data = {
        "text": ["", "7", "3", "x", "9"],
        "conf": ["-1", "10", "85", "99", "40"],
    }
    digit, conf = pick_best_digit_from_tesseract_data(data)
    assert digit == 3
    assert conf == 0.85
