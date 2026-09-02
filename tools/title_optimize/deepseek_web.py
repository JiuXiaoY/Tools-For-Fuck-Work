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
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlparse

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
资深电商视觉分析师与商品信息提取专家，专精于欧洲市场（法国、德国）的客观属性描述。

**Task:**  
根据【商品图片】和【原始标题：{title}】，深度识别该产品的**基础特征**与**差异化特征**，生成一个高密度、去同质化的中文结构化标题（属性短语集合）。该标题将用于欧洲站点的关键词映射与翻译。
**Constraints & Rules:**  
1. **必须包含两大特征组**：  
   - **基础特征（通用必填）**：  
     · 核心品类名称（**必须明确写出**，如“连帽套头卫衣”“全拉链开衫夹克”“防风冲锋衣”等，不得省略或用模糊词替代）。  
     · 版型（修身/常规/宽松）及适用性别（男士/女士/中性）。  
     · 通用功能（如防风、透气、轻量、快干等，需基于图片证据）。  
     · 通用设计元素（如领型、袖长、门襟结构等基础描述）。  
   - **差异化特征（独特点）**：  
     从图片中找出**至少3个区别于同款竞品的物理细节**（禁止涉及材质和具体颜色），例如：  
     *拉链头形状/材质（金属/尼龙/隐形，但只写形态如“金属拉链头”不写材质则可以写“金属”因为金属是材质？——这里要注意，用户禁止材质，所以拉链头如果写“金属”也算材质，应该避免。写“异形拉链头”“双拉链头”等形态。同样，口袋位置、开合方式、缝线走向、刺绣图案形状、帽檐加固方式、袖口调节带、抽绳类型、纽扣数量与布局等。*  
     注意：这些差异化描述**不得涉及面料成分或具体颜色**，但可提及图案类型（如“迷彩印花”“条纹拼接”等）或“纯色”等非具体颜色词语。
2. **关于颜色/图案的允许与禁止**：  
   - **禁止**：任何具体颜色名称（如红、蓝、绿、黑、白、灰、卡其等）。  
   - **允许**：描述图案类型或纯色属性，如“纯色”“印花”“迷彩”“条纹”“格纹”“波点”“抽象几何”等，不限定具体色相。
3. **材质完全禁止**：不得出现任何面料成分词汇（如棉、聚酯、尼龙、羊毛、抓绒等）。
4. **强制品类词**：标题中必须包含核心品类名词，且置于显要位置（建议开头或紧随差异化特征之后）。
5. **去营销化**：严禁使用“爆款”“时尚”“气质”“新款”“经典”“百搭”等主观或时效性词汇。
6. **融合规则**：将原标题中的有效信息（如品牌、型号等）与图片新发现融合，剔除冗余或错误描述。各属性间用空格分隔，不添加逗号或标点。
7. **输出格式**：直接输出优化后的中文标题（紧凑短语序列），**绝对不输出任何分析、解释或额外文字**。
8. **多样性强化**：每次生成时，主动选择图片中**最不常见**的3个差异化细节作为标题开头，确保即使同款不同批也产出不同标题结构；基础特征（含品类词）完整保留，顺序可灵活调整。这是最新规则"""


ASSISTANT_SEL = "div.ds-assistant-message-main-content"


def load_lines(path: Path) -> list[str]:
    return [l.strip() for l in path.read_text(encoding="utf-8").strip().splitlines() if l.strip()]


def download_image(index: int, url: str) -> Path:
    """Download the image for line `index` (1-based) to a unique temp file.

    Returns the saved path; raises on HTTP/IO errors so the caller can retry.
    """
    import requests as req

    name = Path(urlparse(url).path).name or "image.jpg"
    out = BASE / "temp_photo" / f"{index:04d}_{name}"
    out.parent.mkdir(parents=True, exist_ok=True)
    resp = req.get(url, timeout=30)
    resp.raise_for_status()
    out.write_bytes(resp.content)
    return out


def last_assistant_text(page) -> str:
    """返回页面上最后一条助手回复文本(发送前用于记录基线)。"""
    locator = page.locator(ASSISTANT_SEL)
    texts: list[str] = []
    for m in locator.all():
        try:
            t = m.inner_text().strip()
        except Exception:
            continue
        if t:
            texts.append(t)
    return texts[-1] if texts else ""


def extract_last_response(page, previous_text: str = "", timeout: int = 180) -> str:
    """等待生成结束并提取最后一条助手回复(排除思考过程)。

    DeepSeek 页面中,最终回复渲染在 div.ds-assistant-message-main-content 内,
    思考过程("正在思考/分析请求…")在独立容器中,不会进入该选择器。
    previous_text 为发送前页面上已有的最后一条回复(基线):新结果必须不再是
    这条旧消息,否则旧回复会被误当成本次结果(重复)。Stop 按钮选择器在部分
    界面版本下可能失效,因此完成判定以"新文本连续 3 秒无变化"为主。
    超时:有新文本且非基线则兜底返回;否则抛异常(走 FAILED/重试)。
    """
    locator = page.locator(ASSISTANT_SEL)
    stop_btn = page.locator("button:has-text('Stop')")
    deadline = time.monotonic() + timeout
    last_text, stable = "", 0
    while time.monotonic() < deadline:
        texts: list[str] = []
        for m in locator.all():
            try:
                t = m.inner_text().strip()
            except Exception:
                continue  # 元素被 DOM 更新替换,跳过
            if t:
                texts.append(t)
        cur = texts[-1] if texts else ""
        if cur and cur == last_text:
            stable += 1
            if stable >= 3 and cur != previous_text and not stop_btn.is_visible():
                return cur
        else:
            stable = 0
        last_text = cur
        time.sleep(1)
    if last_text and last_text != previous_text:
        return last_text
    raise RuntimeError("No new assistant response found")


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

        # Image prefetch pipeline: download the next image in a background
        # thread while the current item is being analyzed/sent, so download
        # latency overlaps with AI processing time.
        executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="img-dl")
        prefetch: Future | None = None  # future for the CURRENT item, submitted last round

        for i, (url, title) in enumerate(zip(links, titles), 1):
            _log.info("[%d/%d] %s", i, len(links), title[:60])

            try:
                # This item's image was already prefetched during the previous
                # item's analysis (the first item downloads synchronously)
                if prefetch is not None:
                    img_path = prefetch.result()
                else:
                    img_path = download_image(i, url)
                _log.info("  Downloaded: %s", img_path.name)

                # Pre-download the NEXT image while this item is being processed
                if i < len(links):
                    prefetch = executor.submit(download_image, i + 1, links[i])
                    _log.info("  Prefetching next image (%d/%d)", i + 1, len(links))

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
                time.sleep(10)  # ensure image is fully processed

                # Type prompt
                prompt = PROMPT_TEMPLATE.format(title=title)
                textarea = page.locator("textarea").first
                textarea.fill(prompt)
                time.sleep(1)

                # Send
                prev_text = last_assistant_text(page)  # 基线:发送前页面上已有的最后一条消息
                page.keyboard.press("Enter")
                _log.info("  Prompt sent, waiting for response...")
                time.sleep(15)  # initial wait for model to start responding

                # Wait for response to finish and extract last assistant message
                response_text = extract_last_response(page, previous_text=prev_text)
                results.append(response_text)
                _log.info("  Response: %s", response_text[:80])
                success += 1

            except Exception as exc:
                _log.error("  FAILED: %s", exc)
                results.append("[FAILED]")
                failed_items.append((i - 1, url, title))
                errors += 1
                prefetch = None  # no prefetched image for next item — fall back to sync download

            finally:
                # Clean up image
                if 'img_path' in dir() and img_path.exists():
                    img_path.unlink()
                    _log.info("  Deleted: %s", img_path.name)

            # Brief pause between requests
            if i < len(links):
                time.sleep(5)

        executor.shutdown(wait=True)

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
                    img_path = download_image(idx + 1, url)

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
                    prev_text = last_assistant_text(page)
                    page.keyboard.press("Enter")
                    _log.info("    Prompt sent, waiting...")
                    time.sleep(15)

                    response_text = extract_last_response(page, previous_text=prev_text)
                    results[idx] = response_text
                    errors -= 1
                    _log.info("    OK: %s", response_text[:80])

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
