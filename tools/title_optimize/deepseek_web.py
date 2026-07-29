"""DeepSeek web automation — upload images, get title optimization.

Requirements:
    pip install playwright
    playwright install chromium

Usage:
    # First run — login manually, then browser state is saved
    python tools/title_optimize/deepseek_web.py

    # Subsequent runs — auto-login via saved state
    python tools/title_optimize/deepseek_web.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from services.logger import get_logger
from config import Config

BASE = Path(__file__).resolve().parent
STATE_FILE = BASE / "deepseek_state.json"  # saved browser auth state
ORIGIN_LINK = BASE / "origin_link"
ORIGIN_TITLE = BASE / "origin_title"
OPTIMIZE_TITLE = BASE / "optimize_title"

_log = get_logger("deepseek_web")

DEEPSEEK_URL = "https://chat.deepseek.com/"

PROMPT_TEMPLATE = """**Role:**
你是一位资深的电商视觉分析师与商品信息提取专家。

**Task:**
根据我提供的【商品图片】和【原始标题：{title}】，深度识别产品的客观物理特征，并优化/扩写为一个高密度、结构化的中文商品标题（或属性短语集合）。该描述将用于后续的跨境电商 SEO 关键词精准映射。

**Constraints & Rules:**
1. **执行“五要素”视觉扫描**：请仔细观察图片，必须且只能根据视觉事实，提取并补全以下信息：
   - 核心品类（如：连帽卫衣、开衫夹克、冲锋衣等）
   - 可视材质/触感（如：纯棉、抓绒、针织、防水面料等）
   - 版型与受众（如：男士、修身、宽松、常规）
   - 关键细节设计（极度重要：领型、袖长、图案、拉链类型、纽扣位置、口袋样式、罗纹袖口、抽绳等）
   - 风格与可视场景（如：运动、户外、休闲、工装）
2. **客观与去营销化**：严禁使用主观营销词汇（如：爆款、时尚、气质、新款、2026等），只保留客观物理属性。
3. **融合与重组**：将原始标题中的有效信息与图片中新发现的特征完美融合，去除原始标题中的废话或错误信息。
4. **输出格式**：直接输出优化后的中文标题（建议采用“核心词 + 细节属性短语”的紧凑形式），**绝对不要输出任何分析过程、解释或多余的标点寒暄**。"""


def load_lines(path: Path) -> list[str]:
    return [l.strip() for l in path.read_text(encoding="utf-8").strip().splitlines() if l.strip()]


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _log.error("playwright not installed. Run: pip install playwright && playwright install chromium")
        return

    cfg = Config()

    links = load_lines(ORIGIN_LINK)
    titles = load_lines(ORIGIN_TITLE)
    if len(links) != len(titles):
        _log.error("Mismatch: %d links vs %d titles", len(links), len(titles))
        return

    results: list[str] = []
    success = 0
    errors = 0
    failed_items: list[tuple[int, str, str]] = []  # (index, url, title)

    _log.info("Opening DeepSeek web (%d titles)...", len(links))
    _log.info("Browser state: %s", STATE_FILE.name)

    with sync_playwright() as p:
        # Reuse saved login state
        if STATE_FILE.exists():
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(BASE / "browser_data"),
                headless=False,
            )
        else:
            _log.info("No saved state — please log in manually in the browser window")
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(BASE / "browser_data"),
                headless=False,
            )

        page = context.new_page()

        # Navigate to DeepSeek
        page.goto(DEEPSEEK_URL, wait_until="domcontentloaded")
        _log.info("Opened %s", DEEPSEEK_URL)

        # Wait for user to log in (if first time)
        if not STATE_FILE.exists():
            _log.info("========================================")
            _log.info("ACTION: Log in to DeepSeek in the browser")
            _log.info("Once logged in, press Enter here to continue...")
            _log.info("========================================")
            input()
            context.storage_state(path=str(STATE_FILE))
            _log.info("Login state saved to %s", STATE_FILE.name)

        # Wait for chat page to fully load
        page.wait_for_selector("textarea, [contenteditable]", timeout=30000)
        time.sleep(2)
        _log.info("DeepSeek chat ready")

        for i, (url, title) in enumerate(zip(links, titles), 1):
            _log.info("[%d/%d] %s", i, len(links), title[:60])

            try:
                # Download image first
                import requests as req
                img_path = BASE / "temp_photo" / url.split("/")[-1]
                img_path.parent.mkdir(parents=True, exist_ok=True)
                resp = req.get(url, timeout=30)
                resp.raise_for_status()
                img_path.write_bytes(resp.content)
                _log.info("  Downloaded: %s", img_path.name)

                # New chat — click "New Chat" button
                new_chat_btn = page.locator("text=New Chat").first
                if new_chat_btn.is_visible():
                    new_chat_btn.click()
                    time.sleep(1)

                # Switch to vision mode (识图模式)
                vision_btn = page.locator('div[data-model-type="vision"][role="radio"]')
                if vision_btn.is_visible():
                    vision_btn.click()
                    _log.info("  Switched to vision mode")
                    time.sleep(1)

                # Upload image
                file_input = page.locator('input[type="file"]')
                file_input.set_input_files(str(img_path.resolve()))
                _log.info("  Image uploaded, waiting 3s for processing...")
                time.sleep(15)  # ensure image is fully processed

                # Type prompt
                prompt = PROMPT_TEMPLATE.format(title=title)
                textarea = page.locator("textarea").first
                textarea.fill(prompt)
                time.sleep(1)

                # Send
                page.keyboard.press("Enter")
                _log.info("  Prompt sent, waiting for response...")
                time.sleep(15)  # initial wait for model to start responding

                # Wait for response to finish (stop button disappears)
                stop_btn = page.locator("button:has-text('Stop')")
                if stop_btn.is_visible():
                    _log.info("  Still generating, waiting...")
                    stop_btn.wait_for(state="hidden", timeout=120000)
                    time.sleep(2)

                # Extract last assistant message
                messages = page.locator("[class*='message'], [class*='assistant']").all()
                if messages:
                    response_text = messages[-1].inner_text()
                    results.append(response_text.strip())
                    _log.info("  Response: %s", response_text.strip()[:80])
                    success += 1
                else:
                    raise RuntimeError("Could not find assistant response")

            except Exception as exc:
                _log.error("  FAILED: %s", exc)
                results.append("[FAILED]")
                failed_items.append((i - 1, url, title))
                errors += 1

            finally:
                # Clean up image
                if 'img_path' in dir() and img_path.exists():
                    img_path.unlink()
                    _log.info("  Deleted: %s", img_path.name)

            # Brief pause between requests
            if i < len(links):
                time.sleep(5)

        # ── Retry failed items ──
        max_retry_rounds = cfg.retry_max_rounds_deepseek
        retry_round = 0
        while failed_items and retry_round < max_retry_rounds:
            retry_round += 1
            _log.info("")
            _log.info("Retry round %d: %d failed item(s)", retry_round, len(failed_items))
            time.sleep(5)

            still_failed: list[tuple[int, str, str]] = []
            for idx, url, title in failed_items:
                _log.info("  Retry [%d]: %s", idx + 1, title[:60])
                img_path: Path | None = None
                try:
                    import requests as req
                    img_path = BASE / "temp_photo" / url.split("/")[-1]
                    img_path.parent.mkdir(parents=True, exist_ok=True)
                    resp = req.get(url, timeout=30)
                    resp.raise_for_status()
                    img_path.write_bytes(resp.content)

                    new_chat_btn = page.locator("text=New Chat").first
                    if new_chat_btn.is_visible():
                        new_chat_btn.click()
                        time.sleep(1)

                    vision_btn = page.locator('div[data-model-type="vision"][role="radio"]')
                    if vision_btn.is_visible():
                        vision_btn.click()
                        time.sleep(1)

                    file_input = page.locator('input[type="file"]')
                    file_input.set_input_files(str(img_path.resolve()))
                    time.sleep(15)

                    prompt = PROMPT_TEMPLATE.format(title=title)
                    textarea = page.locator("textarea").first
                    textarea.fill(prompt)
                    time.sleep(1)
                    page.keyboard.press("Enter")
                    _log.info("    Prompt sent, waiting...")
                    time.sleep(15)

                    stop_btn = page.locator("button:has-text('Stop')")
                    if stop_btn.is_visible():
                        stop_btn.wait_for(state="hidden", timeout=120000)
                        time.sleep(2)

                    messages = page.locator("[class*='message'], [class*='assistant']").all()
                    if messages:
                        response_text = messages[-1].inner_text().strip()
                        results[idx] = response_text
                        errors -= 1
                        _log.info("    OK: %s", response_text[:80])
                    else:
                        raise RuntimeError("No response")

                except Exception as exc:
                    _log.warning("    FAILED: %s", exc)
                    still_failed.append((idx, url, title))
                finally:
                    if img_path is not None and img_path.exists():
                        img_path.unlink()
                time.sleep(3)

            failed_items = still_failed

        if failed_items:
            _log.warning("Gave up on %d items after %d rounds", len(failed_items), max_retry_rounds)

        context.close()

    # Write results
    OPTIMIZE_TITLE.write_text("\n".join(results), encoding="utf-8")

    _log.info("=" * 50)
    _log.info("Done: %d success, %d failed → %s", len(links) - errors, errors, OPTIMIZE_TITLE.name)
    if errors:
        _log.warning("Unresolved: %d [FAILED] placeholders in output", errors)


if __name__ == "__main__":
    main()
