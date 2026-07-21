"""Word cleaning pipeline for hotwords results.

Each cleaner is a callable that takes list[str] and returns list[str].
Apply in sequence via clean_all().
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

# ── brand list (loaded once at import) ──────────────────────────────

_BRAND_FILE = Path(__file__).resolve().parent / "brand.md"


def _load_brands(path: Path) -> set[str]:
    """Load brand names from file, one per line, lowercase."""
    if not path.exists():
        return set()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return {line.strip().lower() for line in lines if line.strip()}


_BRANDS: set[str] = _load_brands(_BRAND_FILE)

# Precompile brand regex patterns with \b word boundaries
_BRAND_PATTERNS: list[re.Pattern] = [
    re.compile(rf"\b{re.escape(b)}\b") for b in _BRANDS
]


# ── individual cleaners ────────────────────────────────────────────

def strip_whitespace(words: list[str]) -> list[str]:
    """Strip leading/trailing whitespace from each word."""
    return [w.strip() for w in words]


def drop_empty(words: list[str]) -> list[str]:
    """Remove blank / empty entries."""
    return [w for w in words if w]


def drop_short(words: list[str], min_len: int = 2) -> list[str]:
    """Remove words shorter than min_len characters."""
    return [w for w in words if len(w) >= min_len]


def normalize_case(words: list[str]) -> list[str]:
    """Convert all words to lowercase."""
    return [w.lower() for w in words]


def drop_single_word(words: list[str]) -> list[str]:
    """Remove entries that are a single word (no spaces)."""
    return [w for w in words if " " in w]


def drop_brands(words: list[str]) -> list[str]:
    """Remove entries where any whole word/token exactly matches a brand from brand.md."""
    if not _BRAND_PATTERNS:
        return words
    out: list[str] = []
    for w in words:
        if not any(p.search(w) for p in _BRAND_PATTERNS):
            out.append(w)
    return out


def drop_numeric_only(words: list[str]) -> list[str]:
    """Remove entries that consist only of digits / punctuation."""
    return [w for w in words if not re.fullmatch(r"[\d\s.,;:!?\-–—+/*()\[\]{}'\"«»%$€£¥]+", w)]


def drop_urls(words: list[str]) -> list[str]:
    """Remove entries that look like URLs."""
    return [w for w in words if not re.search(r"https?://|www\.", w)]


def drop_excessive_special(words: list[str], ratio: float = 0.5) -> list[str]:
    """Remove entries where >ratio of characters are non-alphanumeric (excluding spaces)."""
    out: list[str] = []
    for w in words:
        stripped = w.replace(" ", "")
        if not stripped:
            continue
        special = sum(1 for c in stripped if not c.isalnum())
        if special / len(stripped) <= ratio:
            out.append(w)
    return out


def deduplicate(words: list[str]) -> list[str]:
    """Remove duplicates while preserving order."""
    seen: set[str] = set()
    out: list[str] = []
    for w in words:
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


def drop_reordered(words: list[str]) -> list[str]:
    """For 2-word entries with same tokens in different order, keep only the first.

    Example: 'baggy jogginghose' and 'jogginghose baggy' → keep first only.
    """
    seen: set[frozenset[str]] = set()
    out: list[str] = []
    for w in words:
        tokens = frozenset(w.split())
        if len(tokens) == 2 and tokens in seen:
            continue
        seen.add(tokens)
        out.append(w)
    return out


# ── pipeline ───────────────────────────────────────────────────────

DEFAULT_PIPELINE: list[Callable[[list[str]], list[str]]] = [
    strip_whitespace,
    # drop_empty,
    # drop_short,
    normalize_case,
    drop_single_word,
    drop_brands,
    drop_reordered,
    # drop_numeric_only,
    # drop_urls,
    # drop_excessive_special,
    deduplicate,
]


# ── classification ─────────────────────────────────────────────────

def classify(words: list[str]) -> dict[str, list[str]]:
    """Split words into buckets: herren, damen, other."""
    buckets: dict[str, list[str]] = {"herren": [], "damen": [], "other": []}
    for w in words:
        if "herren" in w:
            buckets["herren"].append(w)
        elif "damen" in w:
            buckets["damen"].append(w)
        else:
            buckets["other"].append(w)
    return buckets


def clean_all(words: list[str], steps: list[Callable[[list[str]], list[str]]] | None = None) -> list[str]:
    """Run the full cleaning pipeline on a list of words."""
    if steps is None:
        steps = DEFAULT_PIPELINE
    result = words
    for step in steps:
        result = step(result)
    return result


def clean_with_report(words: list[str], steps: list[Callable[[list[str]], list[str]]] | None = None) -> tuple[list[str], list[str]]:
    """Run the pipeline and return (cleaned_words, log_lines)."""
    if steps is None:
        steps = DEFAULT_PIPELINE
    log: list[str] = []
    result = words
    for step in steps:
        before = len(result)
        result = step(result)
        log.append(f"  {step.__name__}: {before} → {len(result)} ({before - len(result)} removed)")
    return result, log
