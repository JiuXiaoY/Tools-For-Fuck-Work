"""Collect hotwords from amz123 API and save extracted words to tools/result/ directory.

Loop mode (default):
    Reads keywords from tools/needToCollect/needToCollect.md (one per line),
    fetches hotwords for each keyword, cleans, classifies, and saves to result/.

Single mode:
    python tools/hotwords.py --single --keyword dress --country de --category tops

Usage:
    python tools/hotwords.py                        # loop all keywords
    python tools/hotwords.py --country us            # loop, different country
    python tools/hotwords.py --single --keyword dress  # single query
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# Ensure project root in sys.path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from services.logger import get_logger
from config import Config
from cleaner import clean_with_report, classify

# Fix Windows console encoding for German characters (ß, Ü, etc.)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_URL = "https://api.amz123.com/search/v1/hotwords/search"
BASE_DIR = Path(__file__).resolve().parent
RESULT_DIR = BASE_DIR / "result"
KEYWORDS_FILE = BASE_DIR / "needToCollect.md"

PAGE_SIZE = 200
PAGE_NUM = 1
REQUEST_INTERVAL = 2.0      # seconds between API calls
REQUEST_TIMEOUT = 30

_log = get_logger("hotwords")


# ── helpers ─────────────────────────────────────────────────────────

def load_keywords(path: Path) -> list[str]:
    """Read keywords from file, one per line, skipping blanks."""
    if not path.exists():
        _log.error("Keywords file not found: %s", path)
        sys.exit(1)
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    return [line.strip() for line in lines if line.strip()]


def build_payload(
    keyword: str = "",
    country: str = "",
    category: str = "",
    sort_mode: str = "new_rank",
    page_size: int = PAGE_SIZE,
    page_num: int = PAGE_NUM,
) -> dict:
    """Build the request payload matching the amz123 hotwords API contract.

    country: 目标站点国家码;留空时回退到 Config.hotwords_country 配置值.

    sort_mode:
        "new_rank"    — sort by ranking (order=1), keep all results
        "fluctuation" — sort by fluctuation desc (order=-1), filter fluctuation < -90000
    """
    condition = "fluctuation" if sort_mode == "fluctuation" else "new_rank"
    order = -1 if sort_mode == "fluctuation" else 1
    if not country:
        country = Config().hotwords_country
    return {
        "word": keyword,
        "country": country,
        "ranking_this_week": [],
        "fluctuation_range": [],
        "word_len_range": [],
        "click_range": [],
        "conversion_range": [],
        "ne_word": "",
        "top3_brand": "",
        "top3_category": category,
        "fluctuation_use_abs": 1,
        "page": {
            "size": page_size,
            "num": page_num,
            "sorts": [{"condition": condition, "order": order}],
        },
    }


def fetch_hotwords(payload: dict) -> dict:
    """Call the amz123 hotwords API and return the raw JSON response."""
    resp = requests.post(API_URL, json=payload, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def extract_words(data: dict, sort_mode: str, cfg: Config) -> list[str]:
    """Extract 'word' field from each row, applying configured filters.

    sort_mode:
        "new_rank"    — tiered filter by result count (configurable)
        "fluctuation" — filter by fluctuation threshold (configurable)
    """
    rows = data.get("data", {}).get("rows", [])
    total = len(rows)
    words: list[str] = []

    for row in rows:
        word = row.get("word")
        if not word or not str(word).strip():
            continue

        if sort_mode == "fluctuation" and cfg.hotwords_fluc_enabled:
            fluc = _int_or_zero(row.get("fluctuation"))
            if fluc >= cfg.hotwords_fluc_threshold:
                continue

        elif sort_mode == "new_rank" and cfg.hotwords_rank_enabled:
            rank = _int_or_zero(row.get("new_rank"))
            if total >= 160 and rank >= cfg.hotwords_rank_threshold_high:
                continue
            if 40 <= total < 160 and rank >= cfg.hotwords_rank_threshold_mid:
                continue
            # total < 40: no filter

        words.append(str(word).strip())
    return words


def _int_or_zero(val: object) -> int:
    try:
        return int(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def save_categorized(buckets: dict[str, list[str]], country: str, ts: str) -> Path:
    """Write categorized words to a timestamped file under result/.

    Format:
        【herren】
        word1
        【damen】
        ...
        【other】
        ...
    """
    filename = f"{ts}_{country}.txt"
    out_path = RESULT_DIR / filename

    lines: list[str] = []
    for label in ("herren", "damen", "other"):
        lines.append(f"【{label}】")
        lines.extend(buckets.get(label, []))
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ── main ────────────────────────────────────────────────────────────

def main() -> None:
    cfg = Config()
    parser = argparse.ArgumentParser(
        description="Collect hotwords from amz123 API, extract word field, save to tools/result/"
    )
    parser.add_argument("--single", action="store_true",
                        help="Single-keyword mode (otherwise loops over needToCollect.md)")
    parser.add_argument("--keyword", default="",
                        help="Search keyword → payload.word (only in --single mode)")
    parser.add_argument("--country", default=cfg.hotwords_country,
                        help=f"Target country → payload.country (default: {cfg.hotwords_country})")
    parser.add_argument("--category", default="",
                        help="Top3 category filter → payload.top3_category")

    args = parser.parse_args()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Single mode ──
    if args.single:
        _log.info("Single mode: keyword=%s  country=%s  category=%s",
                  args.keyword or "(all)", args.country, args.category or "(all)")
        try:
            payload = build_payload(args.keyword, args.country, args.category)
            raw = fetch_hotwords(payload)
        except requests.RequestException as exc:
            _log.error("Request failed: %s", exc)
            sys.exit(1)

        words = extract_words(raw)
        _log.info("Fetched %d words (total=%d  status=%s)",
                   len(words), raw.get("data", {}).get("total", 0), raw.get("status"))

        if not words:
            _log.info("No words found.")
            return

        cleaned, report = clean_with_report(words)
        for line in report:
            _log.info(line)

        buckets = classify(cleaned)
        out_path = save_categorized(buckets, args.country, ts)
        _log.info("herren=%-5d  damen=%-5d  other=%-5d",
                  len(buckets["herren"]), len(buckets["damen"]), len(buckets["other"]))
        _log.info("Saved %d words (raw: %d) → %s", len(cleaned), len(words), out_path.name)
        return

    # ── Loop mode ──
    keywords = load_keywords(KEYWORDS_FILE)
    _log.info("Loop mode: %d keywords  country=%s  category=%s  mode=%s",
              len(keywords), args.country, args.category or "(all)",
              "dual" if cfg.hotwords_dual_mode else cfg.hotwords_single_mode)
    _log.info("")

    all_words: list[str] = []  # combined: fluctuation first, then new_rank
    fluc_words_list: list[str] = []
    rank_words_list: list[str] = []
    errors = 0
    failed: list[str] = []

    def _fetch_one(kw: str, sort_mode: str) -> list[str]:
        """Fetch words for one keyword in one sort mode. Returns empty list on failure."""
        payload = build_payload(kw, args.country, args.category, sort_mode=sort_mode)
        raw = fetch_hotwords(payload)
        return extract_words(raw, sort_mode=sort_mode, cfg=cfg)

    # Precompute active modes
    if cfg.hotwords_dual_mode:
        modes = ["fluctuation", "new_rank"]
    else:
        modes = [cfg.hotwords_single_mode]

    for i, kw in enumerate(keywords, 1):
        _log.info("[%3d/%d] %s", i, len(keywords), kw)
        ok = True
        try:
            for mi, mode in enumerate(modes):
                words = _fetch_one(kw, mode)
                if mode == "fluctuation":
                    fluc_words_list.extend(words)
                else:
                    rank_words_list.extend(words)
                _log.info("  %s: %d words", mode, len(words))
                if mi < len(modes) - 1:
                    time.sleep(0.5)
        except Exception as exc:
            _log.warning("  FAILED: %s", exc)
            errors += 1
            failed.append(kw)
            ok = False
        if ok:
            _log.info("  → total %d words", len(fluc_words_list) + len(rank_words_list))
        time.sleep(REQUEST_INTERVAL)

    # ── Retry failed keywords ──
    max_rounds = cfg.retry_max_rounds_hotwords
    retry_round = 0
    while failed and retry_round < max_rounds:
        retry_round += 1
        _log.info("")
        _log.info("Retry round %d: %d failed keyword(s)", retry_round, len(failed))
        time.sleep(3)
        still_failed: list[str] = []
        for kw in failed:
            _log.info("  Retrying: %s", kw)
            try:
                for mi, mode in enumerate(modes):
                    words = _fetch_one(kw, mode)
                    if mode == "fluctuation":
                        fluc_words_list.extend(words)
                    else:
                        rank_words_list.extend(words)
                    _log.info("    %s: %d words", mode, len(words))
                    if mi < len(modes) - 1:
                        time.sleep(0.5)
                _log.info("    → OK")
            except Exception as exc:
                _log.warning("    FAILED: %s", exc)
                still_failed.append(kw)
            time.sleep(REQUEST_INTERVAL)
        failed = still_failed

    if failed:
        _log.warning("Gave up after %d retry rounds, %d keywords still failed: %s",
                     max_rounds, len(failed), failed)
    else:
        _log.info("All keywords collected successfully")

    # ── Combine: all fluctuation words first, then new_rank words ──
    combined_count = len(fluc_words_list) + len(rank_words_list)
    _log.info("")
    _log.info("Combining: %d fluctuation + %d new_rank = %d total",
              len(fluc_words_list), len(rank_words_list), combined_count)
    all_words = fluc_words_list + rank_words_list

    # ── Clean ──
    _log.info("")
    _log.info("Cleaning...")
    cleaned, report = clean_with_report(all_words)
    for line in report:
        _log.info(line)

    # ── Classify & save ──
    buckets = classify(cleaned)
    out_path = save_categorized(buckets, args.country, ts)
    _log.info("herren=%-5d  damen=%-5d  other=%-5d",
              len(buckets["herren"]), len(buckets["damen"]), len(buckets["other"]))
    _log.info("Saved %d words (raw: %d, errors: %d) → %s",
              len(cleaned), len(all_words), errors, out_path.name)
    _log.info("%s", "=" * 50)
    _log.info("Done.")


if __name__ == "__main__":
    main()
