"""Shared logging — all modules write to logs/{date}_{8chars}.log

Usage:
    from services.logger import get_logger
    log = get_logger(__name__)          # or get_logger("hotwords")
    log.info("message")
    log.info("detail")
    log.warning("issue")
    log.error("failure")

Naming:  logs/20250714_a1b2c3d4.log
    - Same date → reuses existing file
    - New date → generates new random suffix
"""

from __future__ import annotations

import logging
import secrets
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"

# Module-level state
_log_file: Path | None = None
_initialized: bool = False


def _resolve_log_path() -> Path:
    """Find today's log file or create a new one."""
    today = datetime.now().strftime("%Y%m%d")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Try to reuse an existing file from today
    existing = sorted(LOG_DIR.glob(f"{today}_????????.log"))
    if existing:
        return existing[0]

    # Create new
    suffix = secrets.token_hex(4)  # 8 hex chars
    return LOG_DIR / f"{today}_{suffix}.log"


def _init_root_logger() -> Path:
    """Set up the root logger with file + console handlers. Returns log path."""
    global _log_file, _initialized
    if _initialized:
        return _log_file  # type: ignore[return-value]

    _log_file = _resolve_log_path()
    root = logging.getLogger()
    root.setLevel(logging.WARNING)   # silence third-party libs (PIL, openpyxl, etc.)

    # File handler — DEBUG for our own loggers
    fh = logging.FileHandler(_log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)-5s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(fh)

    # Console handler — INFO and above
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(ch)

    _initialized = True
    return _log_file


def get_logger(name: str = "dealexcel") -> logging.Logger:
    """Get a logger that writes to the shared daily log file.

    Only our loggers get DEBUG — third-party libs stay at WARNING.
    """
    _init_root_logger()
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    return logger


def log_path() -> Path:
    """Return the current log file path."""
    _init_root_logger()
    return _log_file  # type: ignore[return-value]
