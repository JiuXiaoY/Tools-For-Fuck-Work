"""Build German titles: collect → write back.

Calls:
  1. de_collect.py     — populate final_de_title (TODO)
  2. de_write_back.py  — write to column 4 + fill blanks

Usage:
    python tools/title_auto_fill/de_title_build.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from services.logger import get_logger

BASE = Path(__file__).resolve().parent
_log = get_logger("de_title_build")

STEPS = [
    ("Collect titles", BASE / "de_collect.py"),
    ("Write back",     BASE / "de_write_back.py"),
]


def main() -> None:
    for name, script in STEPS:
        _log.info("[%s]", name)
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(BASE),
        )
        if result.returncode != 0:
            _log.error("%s FAILED (code %d)", name, result.returncode)
            sys.exit(1)
        _log.info("%s OK", name)

    _log.info("Done.")


if __name__ == "__main__":
    main()
