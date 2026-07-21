"""Cell-level utilities (pure functions, no openpyxl Workbook dependency)."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from openpyxl.cell.cell import Cell

_TRANSPARENT = {"FFFFFF", "000000", "FFFFFFFF", "00000000", "00FFFFFF"}


def is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def cell_has_fill(cell: Cell) -> bool:
    """True if cell has a visible background fill (not white/transparent)."""
    fill = cell.fill
    if fill is None or fill.fill_type is None:
        return False
    for color in (fill.fgColor, fill.bgColor):
        if color is None:
            continue
        if color.type == "rgb" and color.rgb:
            rgb = color.rgb.upper()
            if len(rgb) == 8:
                rgb = rgb[2:]
            if rgb not in _TRANSPARENT:
                return True
        if color.type == "indexed" and color.indexed not in (None, 0, 64):
            return True
        if color.type == "theme" and color.theme not in (None, 0):
            return True
    return False


def to_decimal(value: Any) -> Decimal | None:
    if is_blank(value):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def round_decimal(value: Decimal, places: int = 2) -> float:
    q = Decimal("1." + "0" * places)
    return float(value.quantize(q, rounding=ROUND_HALF_UP))
