"""Batch process .xlsx files from public/xls_xlsx/ through the pipeline."""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from config import Config
from core.runner import process_file
from services.excel import save, merge_workbooks
from services.logger import get_logger, log_path

BASE = Path(__file__).resolve().parent
log = get_logger("main")


def _resolve_date(cfg: Config) -> str:
    """Parse date_override (YYMMDD) → 'M.DD', or use today."""
    raw = cfg.date_override.strip()
    if raw and len(raw) == 6:
        try:
            month = int(raw[2:4])
            day = int(raw[4:6])
            return f"{month}.{day}"
        except ValueError:
            pass
    today = datetime.now()
    return f"{today.month}.{today.day}"


def _resolve_output(out_dir: Path, date_str: str) -> Path:
    """Find next available filename: {date_str}v1.xlsx, v2, v3..."""
    v = 1
    while True:
        path = out_dir / f"{date_str}v{v}.xlsx"
        if not path.exists():
            return path
        v += 1


def main() -> None:
    cfg = Config()
    src = BASE / cfg.src_dir
    out_dir = BASE / cfg.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    log.info("Log file: %s", log_path().name)

    files = sorted(src.glob("*.xlsx"))
    if not files:
        log.warning("No .xlsx files found in %s", src)
        return

    log.info("Found %d file(s):", len(files))
    for f in files:
        log.info("  %s", f.name)

    date_str = _resolve_date(cfg)
    tmp = _resolve_output(out_dir, date_str)
    log.info("Output: %s", tmp.name)
    log.info("=" * 50)

    try:
        if len(files) == 1:
            shutil.copy(files[0], tmp)
            log.info("Single file, copied")
        else:
            stats = merge_workbooks(files)
            save(stats["workbook"], tmp)
            log.info("Merged %d files, %d images total", len(files), stats["images"])

        # Delete source files if configured
        if cfg.delete_source_after_merge:
            for f in files:
                f.unlink(missing_ok=True)
            log.info("Deleted %d source file(s)", len(files))

        result = process_file(tmp, cfg)

        log.info("Size: %d rows x %d cols", result.worksheet.max_row, result.worksheet.max_column)

    except Exception as exc:
        tmp.unlink(missing_ok=True)
        log.error("FAILED: %s", exc)
        raise

    log.info("=" * 50)
    log.info("Done: %s", tmp.name)


if __name__ == "__main__":
    main()
