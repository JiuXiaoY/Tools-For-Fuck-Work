"""Title optimization via AI — image + original title → optimized title.

Workflow:
  1. Read origin_link + origin_title (one-to-one)
  2. Download each image → send (image + title) to AI model
  3. Write optimized title to optimize_title file
  4. Delete image permanently

Config (in config.py):
    ai_provider = "deepseek"   # or "gemini"
    ai_api_key  = "sk-xxx"
    ai_model    = "deepseek-chat"

Usage:
    python tools/title_optimize/run.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import Config
from services.ai_client import AIClient
from services.logger import get_logger

BASE = Path(__file__).resolve().parent
ORIGIN_LINK = BASE / "origin_link"
ORIGIN_TITLE = BASE / "origin_title"
OPTIMIZE_TITLE = BASE / "optimize_title"

_log = get_logger("title_optimize")

SYSTEM_PROMPT = """你是一个 10 年电商标题优化专家。根据原始中文标题，优化标题。

规则：
1. 只添加词，绝不删除或修改原标题中的任何字词
2. 添加的词要贴合产品特征（款式、材质、风格、季节、性别等）
3. 添加的词放在原标题前面作为前缀修饰
4. 优化后的标题使用中文
5. 直接输出优化后的标题，不要任何解释"""

RETRY_DELAY = 3
MAX_RETRIES = 2
CALL_INTERVAL = 1     # DeepSeek 限制较宽松，1s 即可


def load_lines(path: Path) -> list[str]:
    return [l.strip() for l in path.read_text(encoding="utf-8").strip().splitlines() if l.strip()]


def main() -> None:
    cfg = Config()
    if not cfg.ai_api_key:
        _log.error("ai_api_key not set in config.py")
        return

    links = load_lines(ORIGIN_LINK)
    titles = load_lines(ORIGIN_TITLE)
    if len(links) != len(titles):
        _log.error("Mismatch: %d links vs %d titles", len(links), len(titles))
        return

    try:
        client = AIClient.get(cfg.ai_provider, cfg.ai_api_key, cfg.ai_model)
    except ValueError as exc:
        _log.error("%s", exc)
        return

    results: list[str] = []
    success = 0
    errors = 0
    fatal = False

    _log.info("Model: %s (%s) — text-only mode", cfg.ai_provider, cfg.ai_model)
    _log.info("Processing %d title(s)...", len(links))

    for i, (url, title) in enumerate(zip(links, titles), 1):
        _log.info("[%d/%d] %s", i, len(links), title[:60])

        for attempt in range(1, MAX_RETRIES + 2):
            try:
                optimized = client.chat_with_text(title, SYSTEM_PROMPT)
                results.append(optimized)
                _log.info("  Optimized: %s", optimized[:80])
                success += 1
                break

            except Exception as exc:
                err_msg = str(exc)
                if "403" in err_msg or "401" in err_msg:
                    _log.error("  Auth error: %s", exc)
                    results.append(title)
                    errors += 1
                    fatal = True
                    break
                if attempt <= MAX_RETRIES:
                    _log.warning("  Attempt %d/%d: %s", attempt, MAX_RETRIES + 1, exc)
                    time.sleep(RETRY_DELAY)
                else:
                    _log.error("  FAILED: %s", exc)
                    results.append(title)
                    errors += 1

        if i < len(links) and not fatal:
            time.sleep(CALL_INTERVAL)

    OPTIMIZE_TITLE.write_text("\n".join(results), encoding="utf-8")

    _log.info("=" * 50)
    _log.info("Done: %d success, %d errors → %s", success, errors, OPTIMIZE_TITLE.name)


if __name__ == "__main__":
    main()
