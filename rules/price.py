"""Extract a base price from the entries before the first JPY amount."""

from __future__ import annotations

import re
from decimal import Decimal

_PRICE_RE = re.compile(r"([\d.]+)\s+(EUR|USD|GBP|CAD|AUD|JPY|MXN|AED)\b", re.IGNORECASE)


def extract_price_before_jpy(text: str, *, country: str = "fr") -> Decimal | None:
    """Select the base price according to the configured country's rule."""
    if not text or not str(text).strip():
        return None
    matches = list(_PRICE_RE.finditer(str(text)))
    jpy_at = next((i for i, m in enumerate(matches) if m.group(2).upper() == "JPY"), None)
    if jpy_at is None or jpy_at == 0:
        return None

    country = country.lower()
    if country in ("de", "fr"):
        price = matches[jpy_at - 1]
    elif country == "uk":
        price = next((match for match in matches[:jpy_at] if match.group(2).upper() == "GBP"), None)
    else:
        return None

    if price is None:
        return None
    try:
        return Decimal(price.group(1))
    except Exception:
        return None
