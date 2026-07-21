"""Image backup/restore helpers for column insertion."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from openpyxl.drawing.image import Image
from openpyxl.drawing.spreadsheet_drawing import OneCellAnchor, TwoCellAnchor
from openpyxl.worksheet.worksheet import Worksheet

from config import Config


@dataclass
class ImageSnapshot:
    data: bytes
    width: int
    height: int
    from_col: int
    from_row: int
    from_col_off: int
    from_row_off: int
    to_col: int | None = None
    to_row: int | None = None
    to_col_off: int | None = None
    to_row_off: int | None = None
    ext_cx: int | None = None
    ext_cy: int | None = None


def _shift_col(col: int, insertions: list[tuple[int, int]]) -> int:
    col_1b = col + 1
    for at, count in insertions:
        if col_1b >= at:
            col_1b += count
    return col_1b - 1


def snapshot_images(ws: Worksheet) -> list[ImageSnapshot]:
    ss: list[ImageSnapshot] = []
    for img in ws._images:
        a = img.anchor
        if not isinstance(a, (OneCellAnchor, TwoCellAnchor)):
            continue
        s = ImageSnapshot(data=img._data(), width=img.width, height=img.height,
                          from_col=a._from.col, from_row=a._from.row,
                          from_col_off=a._from.colOff, from_row_off=a._from.rowOff)
        if isinstance(a, OneCellAnchor) and a.ext is not None:
            s.ext_cx, s.ext_cy = a.ext.cx, a.ext.cy
        if isinstance(a, TwoCellAnchor) and a.to is not None:
            s.to_col, s.to_row = a.to.col, a.to.row
            s.to_col_off, s.to_row_off = a.to.colOff, a.to.rowOff
        ss.append(s)
    return ss


def restore_images(ws: Worksheet, ss: list[ImageSnapshot], config: Config) -> int:
    ws._images.clear()
    restored = 0
    for s in ss:
        img = Image(BytesIO(s.data))
        img.width, img.height = s.width, s.height
        if s.to_col is not None and s.to_row is not None:
            a = TwoCellAnchor()
            a._from.col = _shift_col(s.from_col, config.column_insertions)
            a._from.row = s.from_row
            a._from.colOff, a._from.rowOff = s.from_col_off, s.from_row_off
            a.to.col = _shift_col(s.to_col, config.column_insertions)
            a.to.row = s.to_row
            a.to.colOff, a.to.rowOff = s.to_col_off or 0, s.to_row_off or 0
        else:
            a = OneCellAnchor()
            a._from.col = _shift_col(s.from_col, config.column_insertions)
            a._from.row = s.from_row
            a._from.colOff, a._from.rowOff = s.from_col_off, s.from_row_off
            if s.ext_cx and s.ext_cy:
                a.ext.cx, a.ext.cy = s.ext_cx, s.ext_cy
        img.anchor = a
        ws.add_image(img)
        restored += 1
    return restored


def clone_image(img, target_ws, row_offset: int = 0) -> bool:
    """Clone an image to another sheet with optional row offset."""
    a = img.anchor
    if not isinstance(a, (OneCellAnchor, TwoCellAnchor)):
        return False
    s = ImageSnapshot(data=img._data(), width=img.width, height=img.height,
                      from_col=a._from.col, from_row=a._from.row + row_offset,
                      from_col_off=a._from.colOff, from_row_off=a._from.rowOff)
    if isinstance(a, OneCellAnchor) and a.ext is not None:
        s.ext_cx, s.ext_cy = a.ext.cx, a.ext.cy
    if isinstance(a, TwoCellAnchor) and a.to is not None:
        s.to_col, s.to_row = a.to.col, a.to.row + row_offset
        s.to_col_off, s.to_row_off = a.to.colOff, a.to.rowOff

    new_img = Image(BytesIO(s.data))
    new_img.width, new_img.height = s.width, s.height
    if s.to_col is not None and s.to_row is not None:
        na = TwoCellAnchor()
        na._from.col, na._from.row = s.from_col, s.from_row
        na._from.colOff, na._from.rowOff = s.from_col_off, s.from_row_off
        na.to.col, na.to.row = s.to_col, s.to_row
        na.to.colOff, na.to.rowOff = s.to_col_off or 0, s.to_row_off or 0
    else:
        na = OneCellAnchor()
        na._from.col, na._from.row = s.from_col, s.from_row
        na._from.colOff, na._from.rowOff = s.from_col_off, s.from_row_off
        if s.ext_cx and s.ext_cy:
            na.ext.cx, na.ext.cy = s.ext_cx, s.ext_cy
    new_img.anchor = na
    target_ws.add_image(new_img)
    return True
