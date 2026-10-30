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

import argparse
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

PROMPT_TEMPLATE = """你是一名面向德国站和法国站的服装商品标题结构化专家。

请根据【商品图片】和【原始标题：{title}】，生成一行高信息密度的中文长标题。该标题用于后续翻译成德语和法语，同时要覆盖买家可能使用的多种常见搜索词。

【任务目标】
不要把原标题过度精简。除清除无价值词、错误信息和具体颜色外，应尽量保留原标题中有搜索价值的品类、季节、材质、图案、版型、结构和功能，并围绕已确认的商品联想更多准确的搜索叫法。

允许在同一标题中多次出现“夹克”“外套”“棒球服”等核心品类词。相关品类短语应分布在标题开头、中间和结尾，而不是只出现一次。

【长标题写法】
先写完整的主品类短语，再补充基础属性，然后继续加入不同角度的相关搜索短语。

推荐结构：
主品类搜索短语 → 性别与版型 → 关键结构 → 季节及功能搜索短语 → 材质或图案搜索短语 → 其他准确的品类搜索短语

例如，同一件有依据的棒球夹克，可以依次覆盖：
绗缝棒球服夹克外套
秋季运动夹克
棒球服外套
拉链夹克外套
短款运动外套

这些短语可以有合理的品类词重复，但每个短语应增加一种搜索入口。不要只把完全相同的词组原样复制多遍。

【联想扩展规则】
围绕图片与原标题共同确认的商品，主动联想以下搜索词：

1. 同类品类词：例如“棒球服”可扩展为“棒球夹克”“运动夹克”“棒球服外套”；“毛绒连帽外套”可扩展为“毛绒夹克”“连帽外套”“冬季保暖外套”。
2. 材质加品类词：例如“法兰绒夹克外套”“毛绒连帽外套”“绗缝棒球夹克”。
3. 结构加品类词：例如“拉链夹克外套”“纽扣毛绒外套”“短款夹克”“连帽夹克外套”。
4. 季节加品类词：原标题明确为冬季或秋季，或商品结构明显匹配该季节时，可写“冬季外套”“秋季夹克”“秋冬法兰绒外套”。
5. 功能加品类词：原标题明确加绒、毛绒、保暖、防风、防雨等信息时，应写“加绒保暖外套”“冬季保暖夹克”“防风外套”等完整搜索短语，不要把“保暖”“防风”孤立放在末尾。
6. 原标题明确为冲锋衣且图片与之相符时，主动扩展“户外冲锋衣”“防风冲锋衣”等常用叫法。只有原标题、图片文字标识或明确结构支持防水时，才写“防水冲锋衣”“防水外套”；“防泼水”不得改写为“防水”。

联想必须始终指向图片中的同一件商品。不能因为想增加品类词，就把夹克写成毛衣、把普通外套写成专业冲锋衣，或加入不匹配的运动用途。

【保留与清理】
- 优先保留具体品类、性别、版型、季节、显著图案、可信材质、内里、连帽、拉链、纽扣、长短款、保暖及防护功能。
- 不必强行列出三个可见差异点。搜索价值比细节数量更重要。
- “菱格绗缝”等局部描述不要孤立放在标题最前面；有价值时写成“绗缝夹克”“绗缝棒球服外套”等完整短语。
- 普通罗纹袖口、罗纹下摆、翻边、常规缝线、普通包边等低价值细节通常删除。
- 所有口袋细节统一为“带口袋”，最多出现一次。
- “单排扣”“双排扣”等描述统一简化为“带纽扣”。
- 可以保留“纯色”“花卉印花”“迷彩印花”“格纹”等有依据的视觉搜索词，但不得写任何具体颜色名称。
- 删除促销词、平台词、店铺词、尺码、数量代码、无意义型号及重复的营销表达。
- 禁止使用：爆款 时尚 气质 新款 经典 百搭 高端 高级 奢华 潮流 必备 热卖 超值 优质 舒适 显瘦 完美 最佳。

【长度和覆盖要求】
尽量写成长标题，通常覆盖至少 3 至 6 个准确的品类或“属性＋品类”搜索短语，分布在标题不同位置。优先扩展已确认商品的同义品类、季节品类、材质品类和结构品类，不要为了达到长度编造属性。

品类词的合理重复是允许且需要的。例如同一标题可以同时包含“棒球服夹克外套”“运动夹克”“拉链夹克外套”。不要套用普通短标题的去重规则，把这些搜索入口删到只剩一个品类词。

【输出前内部检查】
确认每个扩展短语仍指向同一件商品；功能和材质有依据；没有具体颜色、错误类目、营销词或明显矛盾；保留了原标题中的高价值搜索词；品类词在标题不同位置得到充分覆盖。不要输出检查过程。

【输出格式】
只输出一行中文长标题。各搜索短语之间使用单个空格，不使用标点，不输出分析、解释、标签、前缀或备注。"""


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
    parser = argparse.ArgumentParser(description="DeepSeek title optimization")
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help="Keep successful lines in optimize_title and process only [FAILED] lines",
    )
    args = parser.parse_args()

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

    if args.retry_failed:
        results = load_lines(OPTIMIZE_TITLE)
        if len(results) != len(links):
            _log.error(
                "Cannot resume: %s has %d lines, expected %d",
                OPTIMIZE_TITLE.name,
                len(results),
                len(links),
            )
            return
        retry_indices = [i for i, value in enumerate(results) if value == "[FAILED]"]
        if not retry_indices:
            _log.info("No [FAILED] lines found; nothing to retry")
            return
        work_items = [(i, links[i], titles[i]) for i in retry_indices]
        errors = len(retry_indices)
        _log.info(
            "Resume mode: preserving %d successful lines; retrying %d failed lines",
            len(links) - errors,
            errors,
        )
    else:
        results = [""] * len(links)
        work_items = [(i, url, title) for i, (url, title) in enumerate(zip(links, titles))]
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

        for work_pos, (idx, url, title) in enumerate(work_items):
            item_number = idx + 1
            _log.info("[%d/%d] %s", item_number, len(links), title[:60])

            try:
                # This item's image was already prefetched during the previous
                # item's analysis (the first item downloads synchronously)
                if prefetch is not None:
                    img_path = prefetch.result()
                else:
                    img_path = download_image(item_number, url)
                _log.info("  Downloaded: %s", img_path.name)

                # Pre-download the NEXT image while this item is being processed
                if work_pos + 1 < len(work_items):
                    next_idx, next_url, _ = work_items[work_pos + 1]
                    prefetch = executor.submit(download_image, next_idx + 1, next_url)
                    _log.info(
                        "  Prefetching next image (%d/%d)",
                        next_idx + 1,
                        len(links),
                    )
                else:
                    prefetch = None

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
                was_failed = results[idx] == "[FAILED]"
                results[idx] = response_text
                if was_failed:
                    errors -= 1
                if args.retry_failed:
                    OPTIMIZE_TITLE.write_text("\n".join(results), encoding="utf-8")
                _log.info("  Response: %s", response_text[:80])

            except Exception as exc:
                _log.error("  FAILED: %s", exc)
                if results[idx] != "[FAILED]":
                    errors += 1
                results[idx] = "[FAILED]"
                failed_items.append((idx, url, title))
                prefetch = None  # no prefetched image for next item — fall back to sync download

            finally:
                # Clean up image
                if 'img_path' in dir() and img_path.exists():
                    img_path.unlink()
                    _log.info("  Deleted: %s", img_path.name)

            # Brief pause between requests
            if work_pos + 1 < len(work_items):
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
                    if args.retry_failed:
                        OPTIMIZE_TITLE.write_text("\n".join(results), encoding="utf-8")
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
