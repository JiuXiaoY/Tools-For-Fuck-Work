"""Jenkins pipeline — full automation from .xls to optimized output.

Steps:
  1. xls → xlsx          (tools/xls2xlsx.py)
  2. Preprocess           (preprocess/run.py)
  3. Excel pipeline       (main.py: merge + 13-step pipeline)
  4. Color re-processing  (tools/color_size_deal/color_reprocess.py)
  5. Title optimization   (tools/title_optimize/title_rewrite.py)
  6. Title auto fill      (tools/title_auto_fill/de_title_build.py)
  7. Export SKU            (tools/export_sku/export_sku.py)

Usage:
    python jenkins.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from services.logger import get_logger

BASE = Path(__file__).resolve().parent
_log = get_logger("jenkins")

STEPS = [
    ("xls → xlsx",          BASE / "tools" / "xls2xlsx.py"),
    ("Preprocess",           BASE / "preprocess" / "run.py"),
    ("Excel pipeline",      BASE / "main.py"),
    ("Color re-processing",  BASE / "tools" / "color_size_deal" / "color_reprocess.py"),
    ("Title optimization",    BASE / "tools" / "title_optimize" / "title_rewrite.py"),
    # ("de title build",      BASE / "tools" / "title_auto_fill" / "de_title_build.py"),
    ("Export SKU",            BASE / "tools" / "export_sku" / "export_sku.py"),
]


def main() -> None:
    _log.info("=" * 50)
    _log.info("Jenkins pipeline — %d steps", len(STEPS))
    _log.info("=" * 50)

    for i, (name, script) in enumerate(STEPS, 1):
        _log.info("")
        _log.info("[%d/%d] %s", i, len(STEPS), name)
        _log.info("-" * 30)

        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(BASE),
        )
        if result.returncode != 0:
            _log.error("[%d/%d] %s FAILED (code %d)", i, len(STEPS), name, result.returncode)
            _log.error("Pipeline aborted.")
            sys.exit(1)
        _log.info("[%d/%d] %s OK", i, len(STEPS), name)

    _log.info("")
    _log.info("=" * 50)
    _log.info("All %d steps completed successfully", len(STEPS))


if __name__ == "__main__":
    main()
