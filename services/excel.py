"""Excel workbook I/O: load, save, merge (first sheet only from each file)."""

from __future__ import annotations

import logging
from contextlib import closing
from copy import copy as copy_style
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from services.images import clone_image

logger = logging.getLogger(__name__)


def load(path: Path) -> Workbook:
    return load_workbook(path)


def save(wb: Workbook, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def _copy_style(src, dst) -> None:
    if not src.has_style:
        return
    for attr in ("font", "border", "fill", "number_format", "protection", "alignment"):
        setattr(dst, attr, copy_style(getattr(src, attr)))


def keep_first_worksheet(workbook: Workbook) -> Worksheet:
    """Keep the first worksheet in tab order in an output workbook."""
    first = workbook.worksheets[0]
    for name in workbook.sheetnames:
        if name != first.title:
            del workbook[name]
    first.sheet_state = "visible"
    workbook.active = 0
    return first


def merge_workbooks(paths: list[Path]) -> dict:
    """Append the first worksheet of each input workbook to a single worksheet."""
    if not paths:
        raise ValueError("empty path list")

    target = load(paths[0])
    target_ws = keep_first_worksheet(target)
    total = len(target_ws._images)
    print(f"  [merge] {paths[0].name}: {total}/{total} images kept")

    for fp in paths[1:]:
        with closing(load(fp)) as source:
            src_ws = source.worksheets[0]
            offset = target_ws.max_row

            for row_number, row in enumerate(src_ws.iter_rows(), start=1):
                target_row = row_number + offset
                height = src_ws.row_dimensions[row_number].height
                if height is not None:
                    target_ws.row_dimensions[target_row].height = height
                for cell in row:
                    target_cell = target_ws.cell(row=target_row, column=cell.column)
                    target_cell.value = cell.value
                    _copy_style(cell, target_cell)

            for merged in src_ws.merged_cells.ranges:
                target_ws.merge_cells(
                    start_row=merged.min_row + offset,
                    start_column=merged.min_col,
                    end_row=merged.max_row + offset,
                    end_column=merged.max_col,
                )

            img_count = 0
            for img in src_ws._images:
                try:
                    if clone_image(img, target_ws, row_offset=offset):
                        img_count += 1
                except Exception as exc:
                    logger.warning("Image clone failed in %s: %s", fp.name, exc)
            total += img_count
            print(f"  [merge] {fp.name}: {img_count}/{len(src_ws._images)} images copied")

    return {"workbook": target, "images": total}
