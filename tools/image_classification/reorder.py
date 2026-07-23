"""Reorder image links in Excel: mark non-conforming size chart positions red.

Data source: O-W columns (15-23) of outputs/{date}v1.xlsx

Algorithm:
  - Maintain startCol across rows (1-based, relative to O-W range)
  - For each row, classify all images, then apply:
    Case A: startCol cell IS size chart → mark it red, next startCol = that col
    Case B: startCol has data, not chart → scan right then left; if found mark red
    Case C: startCol empty → scan left; if not found → entire row red
  - No size chart found → entire row red, startCol reset to 1

Usage:
    python tools/image_classification/reorder.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import requests
from openpyxl.styles import PatternFill

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import Config
from services.logger import get_logger

BASE = Path(__file__).resolve().parent
TEMP_DIR = BASE / "images_awaiting"
_log = get_logger("image_reorder")

COL_START = 15
COL_END = 23
def _mark_red(ws, row: int, col: int) -> None:
    """Set cell background to red, persisting regardless of value changes."""
    cell = ws.cell(row=row, column=col)
    from openpyxl.styles import PatternFill
    cell.fill = PatternFill(start_color="FFCCCC", end_color="FFCCCC", fill_type="solid", patternType="solid")
    # Force style flag
    from copy import copy
    if not cell.has_style:
        cell.font = copy(cell.font)


def _resolve_date(cfg: Config) -> str:
    raw = cfg.date_override.strip()
    if raw and len(raw) == 6:
        try:
            month = int(raw[2:4])
            day = int(raw[4:6])
            return f"{month}.{day}"
        except ValueError:
            pass
    from datetime import datetime
    today = datetime.now()
    return f"{today.month}.{today.day}"


def _download(url: str) -> Path | None:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    name = url.split("/")[-1].split("?")[0] or "img.jpg"
    out = TEMP_DIR / name
    for attempt in range(1, 4):
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            out.write_bytes(resp.content)
            return out
        except Exception as exc:
            _log.warning("    Download attempt %d/3 failed: %s", attempt, exc)
            if attempt < 3:
                time.sleep(2)
    return None


def _is_size_chart(img_path: Path, cfg: Config) -> bool:
    from tools.image_classification.classify import _detect_ocr, _detect_opencv, _detect_heuristic

    mode = cfg.img_classify_mode
    scores: dict[str, float] = {}
    if mode in ("heuristic", "all"):
        scores["heuristic"] = _detect_heuristic(img_path)
    if mode in ("ocr", "all"):
        scores["ocr"] = _detect_ocr(img_path, cfg)
    if mode in ("opencv", "all"):
        scores["opencv"] = _detect_opencv(img_path, cfg)

    if mode == "all":
        valid = {k: v for k, v in scores.items() if v > 0.0}
        if not valid:
            return False
        yes = sum(1 for v in valid.values() if v >= 0.5)
        avg = sum(valid.values()) / len(valid)
        return yes >= 2 or avg >= 0.6
    else:
        return scores.get(mode, 0.0) >= 0.5


def main() -> None:
    cfg = Config()
    date_str = _resolve_date(cfg)
    src = Path(__file__).resolve().parent.parent.parent / cfg.out_dir / f"{date_str}v1.xlsx"

    if not src.exists():
        _log.error("Source not found: %s", src)
        return

    import openpyxl
    wb = openpyxl.load_workbook(src)
    ws = wb.active

    _log.info("Source: %s  Rows: %d  Range: O(%d)-W(%d)  Mode: %s",
              src.name, ws.max_row, COL_START, COL_END, cfg.img_classify_mode)

    rows_processed = 0
    rows_red = 0
    start_col = 1  # 1-based within O-W

    for r in range(1, ws.max_row + 1):
        links: list[tuple[int, str]] = []
        for c in range(COL_START, COL_END + 1):
            val = ws.cell(row=r, column=c).value
            if val is None or str(val).strip() == "":
                break
            links.append((c, str(val).strip()))

        if not links:
            continue

        num_cols = len(links)
        rows_processed += 1
        _log.info("[Row %d] %d link(s), startCol=%d", r, num_cols, start_col)

        # Lazy classify: download → classify → delete on demand
        def _check_cell(idx: int) -> bool | None:
            """Return True/False for size chart, or None if download failed."""
            col, url = links[idx]
            p = _download(url)
            if p is None:
                return None
            try:
                result = _is_size_chart(p, cfg)
                _log.info("  col %d: %s", col, "SIZE_CHART" if result else "product")
                return result
            except Exception as exc:
                _log.warning("  col %d: classify failed — %s", col, exc)
                return False
            finally:
                try: p.unlink()
                except OSError: pass

        # Algorithm
        si = min(start_col - 1, num_cols - 1)
        found_col: int | None = None

        # Check start cell first
        r0 = _check_cell(si)
        if r0 is None:
            for col, _ in links:
                _mark_red(ws, r, col)
            rows_red += 1
            start_col = 1
            continue

        if r0:
            found_col = si + 1  # Case A
        else:
            # Case B: scan right
            for j in range(si + 1, num_cols):
                rj = _check_cell(j)
                if rj is None:
                    break
                if rj:
                    found_col = j + 1
                    break
            # If not found, scan left
            if found_col is None:
                for j in range(0, si):
                    rj = _check_cell(j)
                    if rj is None:
                        break
                    if rj:
                        found_col = j + 1
                        break

        if found_col is None:
            for col, _ in links:
                _mark_red(ws, r, col)
            rows_red += 1
            start_col = 1
            _log.info("  → No size chart, row red, startCol=1")
        else:
            target_col = COL_START + found_col - 1
            _mark_red(ws, r, target_col)
            rows_red += 1

            # Copy size chart value + hyperlink to position after last data item
            last_col = COL_START + num_cols - 1
            dest_col = last_col + 1
            if dest_col > COL_END:
                dest_col = COL_END  # clamp to W

            src_cell = ws.cell(row=r, column=target_col)
            dst_cell = ws.cell(row=r, column=dest_col)
            dst_cell.value = src_cell.value
            dst_cell.hyperlink = src_cell.hyperlink

            start_col = found_col
            _log.info("  → Size chart at col %d marked red, copied to col %d, next startCol=%d",
                      target_col, dest_col, start_col)

    wb.save(src)
    wb.close()
    _log.info("Done: %d rows processed, %d rows with red marks", rows_processed, rows_red)


if __name__ == "__main__":
    main()
