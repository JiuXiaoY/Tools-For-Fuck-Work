"""Classify images as size chart vs product photo.

Three detection engines (switchable via config):
  heuristic — PIL-based: aspect ratio / white pixels / color variance / edges
  ocr       — Tesseract: detect size-table keywords (S/M/L/XL, cm, Brust...)
  opencv    — OpenCV: detect table grid lines (HoughLinesP)
  all       — Run all engines, majority vote

Config (config.py):
  img_classify_mode         = "all"
  img_classify_ocr_lang     = "eng+deu"
  img_classify_table_min_lines  = 5

Usage:
    python tools/image_classification/classify.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import Config
from services.logger import get_logger

BASE = Path(__file__).resolve().parent
SRC_DIR = BASE / "images_awaiting"
DST_DIR = BASE
_log = get_logger("image_classify")


# ══════════════════════════════════════════════════════════════════════
#  Engine 1: Heuristic (PIL, always available)
# ══════════════════════════════════════════════════════════════════════

def _detect_heuristic(img_path: Path) -> float:
    """Heuristic detection. Returns confidence 0.0-1.0."""
    img = Image.open(img_path).convert("RGB")
    w, h = img.size

    if max(w, h) > 400:
        scale = 400 / max(w, h)
        small = img.resize((int(w * scale), int(h * scale)))
    else:
        small = img

    n = small.size[0] * small.size[1]

    # White pixels
    pixels = list(small.getdata())
    white = sum(1 for p in pixels if p[0] > 220 and p[1] > 220 and p[2] > 220)
    white_ratio = white / n
    score_w = 1.0 if white_ratio > 0.5 else white_ratio / 0.5

    # Color variance
    stat = ImageStat.Stat(small)
    var = sum(stat.var) / 3 if stat.var else 5000
    score_v = 1.0 if var < 3000 else max(0, 1 - (var - 3000) / 5000)

    # Edge density
    edges = small.filter(ImageFilter.FIND_EDGES)
    ep = list(edges.getdata())
    strong = sum(1 for p in ep if p[0] > 60 or p[1] > 60 or p[2] > 60)
    edge_r = strong / n
    score_e = 1.0 if 5 < edge_r * 100 < 30 else 0.5 if edge_r * 100 < 50 else 0.0

    # Aspect (size charts wider)
    ratio = w / h if h else 1
    score_a = 1.0 if ratio > 1.3 else 0.5 if ratio > 1.0 else 0.0

    return round(score_a * 0.25 + score_w * 0.35 + score_v * 0.25 + score_e * 0.15, 3)


# ══════════════════════════════════════════════════════════════════════
#  Engine 2: OCR (Tesseract)
# ══════════════════════════════════════════════════════════════════════

def _detect_ocr(img_path: Path, cfg: Config) -> float:
    """OCR-based detection. Returns confidence 0.0-1.0."""
    try:
        import easyocr
    except ImportError:
        _log.warning("    OCR skip: easyocr not installed (pip install easyocr)")
        return 0.0

    # Lazy init reader (cached globally)
    if not hasattr(_detect_ocr, "_reader"):
        _detect_ocr._reader = easyocr.Reader(["de", "en"], gpu=False, verbose=False)
    reader = _detect_ocr._reader

    img = Image.open(img_path).convert("RGB")
    w, h = img.size

    # Fast pre-filter: skip if image has too little "texture" (product photos are smooth)
    if max(w, h) > 400:
        scale = 400 / max(w, h)
        img_small = img.resize((int(w * scale), int(h * scale)))
    else:
        img_small = img

    # Fast pre-filter: skip smooth product photos
    import numpy as np
    arr = np.array(img_small.convert("L"))
    edges = np.abs(np.diff(arr, axis=0)).mean() + np.abs(np.diff(arr, axis=1)).mean()
    if edges < 15:
        return 0.0

    try:
        results = reader.readtext(np.array(img_small), detail=0)
        text = " ".join(results)
    except Exception as exc:
        _log.warning("    OCR failed: %s", exc)
        return 0.0

    # Count letters and digits
    alpha_num = sum(1 for c in text if c.isalpha() or c.isdigit())

    _log.info("    OCR: %d chars, %d alpha/num, sample: %s",
              len(text), alpha_num, text[:120].replace('\n', ' '))

    # High text density → likely size chart (tables have lots of numbers/letters)
    # Product photos have very little recognizable text
    if alpha_num > 35:
        return min(1.0, 0.7 + (alpha_num - 35) / 150)
    return 0.0


# ══════════════════════════════════════════════════════════════════════
#  Engine 3: OpenCV table lines
# ══════════════════════════════════════════════════════════════════════

def _detect_opencv(img_path: Path, cfg: Config) -> float:
    """OpenCV-based table-line detection. Returns confidence 0.0-1.0."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        _log.warning("    OpenCV skip: opencv-python not installed (pip install opencv-python)")
        return 0.0

    img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return 0.0

    w, h = img.shape[1], img.shape[0]
    if max(w, h) > 1200:
        scale = 1200 / max(w, h)
        img = cv2.resize(img, (int(w * scale), int(h * scale)))

    # Edge detection
    edges = cv2.Canny(img, 50, 150, apertureSize=3)

    # Hough line detection
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                            minLineLength=img.shape[1] // 4, maxLineGap=20)

    if lines is None:
        return 0.0

    # Count horizontal lines (angle near 0° or 180°)
    h_lines = 0
    for line in lines:
        arr = line.flatten()
        if len(arr) < 4:
            continue
        x1, y1, x2, y2 = arr[:4]
        angle = abs(float(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi))
        if angle < 5 or angle > 175:
            h_lines += 1

    min_lines = cfg.img_classify_table_min_lines
    if h_lines >= min_lines:
        return min(1.0, 0.7 + (h_lines - min_lines) * 0.05)
    return 0.0


# ══════════════════════════════════════════════════════════════════════
#  Main
# ══════════════════════════════════════════════════════════════════════

def main() -> None:
    cfg = Config()
    mode = cfg.img_classify_mode

    if not SRC_DIR.exists():
        _log.error("images_awaiting not found: %s", SRC_DIR)
        return

    files = sorted(SRC_DIR.glob("*"))
    files = [f for f in files if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".bmp")]

    if not files:
        _log.info("No images in images_awaiting")
        return

    _log.info("Classifying %d image(s)  mode=%s", len(files), mode)
    found = 0

    for f in files:
        try:
            img = Image.open(f)
            scores: dict[str, float] = {}

            if mode in ("heuristic", "all"):
                scores["heuristic"] = _detect_heuristic(f)
                _log.info("  %s  heuristic=%.2f", f.name, scores["heuristic"])

            if mode in ("ocr", "all"):
                scores["ocr"] = _detect_ocr(f, cfg)
                _log.info("  %s  ocr=%.2f", f.name, scores["ocr"])

            if mode in ("opencv", "all"):
                scores["opencv"] = _detect_opencv(f, cfg)
                _log.info("  %s  opencv=%.2f", f.name, scores["opencv"])

            # Decision
            if mode == "all":
                # Only count engines that actually ran (skip 0.0 from unavailable engines)
                valid = {k: v for k, v in scores.items() if v > 0.0}
                if not valid:
                    is_chart = False
                    info = "no engine available"
                elif len(valid) == 1:
                    is_chart = list(valid.values())[0] >= 0.5
                    info = f"{list(valid.keys())[0]}={list(valid.values())[0]:.2f}"
                else:
                    yes_count = sum(1 for v in valid.values() if v >= 0.5)
                    avg = sum(valid.values()) / len(valid)
                    is_chart = yes_count >= 2 or avg >= 0.6
                    info = f"votes={yes_count}/{len(valid)} avg={avg:.2f}"
            else:
                val = scores.get(mode, 0.0)
                is_chart = val >= 0.5
                info = f"{mode}={val:.2f}"

            label = "SIZE_CHART" if is_chart else "PRODUCT"
            _log.info("    → %s (%s)", label, info)

            if is_chart:
                img.close()
                dst = DST_DIR / f.name
                shutil.move(str(f), str(dst))
                found += 1
            else:
                img.close()

        except Exception as exc:
            _log.warning("  %s  SKIP: %s", f.name, exc)

    _log.info("Done: %d size charts found", found)


if __name__ == "__main__":
    main()
