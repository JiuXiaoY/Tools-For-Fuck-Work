"""Price extraction rule: find the price immediately before the JPY entry."""

from __future__ import annotations

import re
from decimal import Decimal

_PRICE_RE = re.compile(r"([\d.]+)\s+(EUR|USD|GBP|CAD|AUD|JPY|MXN|AED)\b", re.IGNORECASE)


def extract_price_before_jpy(text: str) -> Decimal | None:
    """In text like \"... 26.04 EUR ... 2482.25 JPY\", return 26.04."""
    if not text or not str(text).strip():
        return None
    matches = list(_PRICE_RE.finditer(str(text)))
    jpy_at = next((i for i, m in enumerate(matches) if m.group(2).upper() == "JPY"), None)
    if jpy_at is None or jpy_at == 0:
        return None
    try:
        return Decimal(matches[jpy_at - 1].group(1))
    except Exception:
        return None
