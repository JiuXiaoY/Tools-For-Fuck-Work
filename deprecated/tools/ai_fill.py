"""AI fill: process column 4 based on column 8 text via Gemini.

Run AFTER python main.py, BEFORE opening the output file.

Usage:
    1. Set gemini_api_key and gemini_prompt_template in config.py
    2. python main.py           (process files through pipeline)
    3. python ai_fill.py        (AI-fill column 4)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config
from services.ai_fill import fill_column_4
from services.logger import get_logger

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "outputs"
_log = get_logger("ai_fill")


def main() -> None:
    cfg = Config()
    if not cfg.gemini_api_key:
        _log.error("gemini_api_key is not set in config.py")
        return

    files = sorted(f for f in OUTPUT_DIR.glob("*.xlsx") if not f.name.startswith("~$"))
    if not files:
        _log.warning("No .xlsx files in outputs/ — run main.py first")
        return

    _log.info("Found %d file(s) in outputs/", len(files))

    for i, fp in enumerate(files, 1):
        _log.info("[%d/%d] %s", i, len(files), fp.name)
        try:
            n = fill_column_4(fp, cfg)
            _log.info("  → %d rows AI-filled", n)
        except Exception as exc:
            _log.error("  FAILED: %s", exc)

    _log.info("Done.")


if __name__ == "__main__":
    main()
