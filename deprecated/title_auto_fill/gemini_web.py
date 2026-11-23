"""Open Gemini web — login session management.

Requirements:
    pip install playwright
    playwright install chromium

Usage:
    python tools/title_optimize/gemini_web.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from services.logger import get_logger

BASE = Path(__file__).resolve().parent
STATE_FILE = BASE / "gemini_state.json"
_log = get_logger("gemini_web")

GEMINI_URL = "https://gemini.google.com/"


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _log.error("playwright not installed. Run: pip install playwright && playwright install chromium")
        return

    _log.info("Opening Gemini...")

    with sync_playwright() as p:
        if STATE_FILE.exists():
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(BASE / "gemini_browser"),
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=ChromeWhatsNewUI",
                ],
            )
        else:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(BASE / "gemini_browser"),
                headless=False,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=ChromeWhatsNewUI",
                ],
            )

        page = context.new_page()
        # Hide webdriver flag
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
        """)
        page.goto(GEMINI_URL, wait_until="domcontentloaded")
        _log.info("Opened Gemini")

        if not STATE_FILE.exists():
            _log.info("========================================")
            _log.info("ACTION: Log in to Gemini in the browser")
            _log.info("Once logged in, press Enter here to continue...")
            _log.info("========================================")
            input()
            context.storage_state(path=str(STATE_FILE))
            _log.info("Login state saved to %s", STATE_FILE.name)
        else:
            _log.info("Already logged in")
            time.sleep(3)

        _log.info("Browser will close in 5s...")
        time.sleep(5)
        context.close()

    _log.info("Done.")


if __name__ == "__main__":
    main()
