"""Preprocess source files — modify public/xls_xlsx/ in-place before pipeline.

Steps are registered in steps/__init__.py -> get_preprocess_steps().

Usage:
    python preprocess/run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import Config
from services.logger import get_logger

from preprocess.steps import get_preprocess_steps

_log = get_logger("preprocess")


def main() -> None:
    cfg = Config()
    src_dir = Path(__file__).resolve().parent.parent / cfg.src_dir
    files = sorted(src_dir.glob("*.xlsx"))

    if not files:
        _log.info("No .xlsx files in %s — nothing to preprocess", src_dir)
        return

    steps = get_preprocess_steps()
    _log.info("Preprocessing %d file(s) with %d step(s)", len(files), len(steps))

    for f in files:
        _log.info("[%s]", f.name)
        wb = openpyxl.load_workbook(f)
        for step in steps:
            step.run(wb, f.name)
        wb.save(f)
        wb.close()

    _log.info("Preprocessing complete")


if __name__ == "__main__":
    main()
