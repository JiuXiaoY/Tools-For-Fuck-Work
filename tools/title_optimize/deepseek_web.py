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

PROMPT_TEMPLATE = """你是一名面向德国站和法国站的服装商品标题结构化专家。

请根据【商品图片】和【原始标题：{title}】，识别产品可被可靠确认的基础特征与差异化特征，生成一个高信息密度、便于后续翻译为德语和法语的中文结构化标题。

该中文标题是德语和法语商品标题的语义中间层，必须使用含义明确、可直接翻译、无歧义的标准服装属性短语。

【信息证据优先级】

1. 商品图片中能够直接观察到的物理特征。
2. 原始标题中明确出现且不与图片冲突的信息。
3. 无法从图片或原标题可靠确认的信息一律不得补充、猜测或推断。

防风、防水、透气、保暖、快干、防晒、弹力等功能，只有在图片存在明确文字、功能图标、结构证据，或原标题明确说明时才能使用。不得仅凭外观推断功能。

【标题必须包含】

一、差异化特征

标题开头必须放置至少3个图片中可见、区别于普通竞品的物理细节。

优先选择最少见、最具体的特征，例如：

- 特殊印花或图案类型
- 异形口袋或口袋数量
- 不对称门襟
- 多层帽体
- 可拆卸结构
- 特殊领型
- 拼接结构
- 袖口或下摆调节结构
- 拉链位置
- 开衩结构
- 收腰或抽绳结构
- 装饰带、徽章、刺绣或贴章
- 上下装组合方式
- 特殊裤型或衣长

不得把“休闲”“简约”“舒适”等泛化词当作差异化特征。

如果图片中的独特元素不足3个，应从可见的领型、门襟、口袋、袖口、下摆、帽型、拼接、版型或上下装结构中选择最具体的细节补足，禁止虚构功能。

二、基础特征

必须完整包含：

1. 核心品类名称  
必须使用唯一、明确且足够具体的品类词，例如：

- 连帽套头卫衣
- 全拉链开衫夹克
- 防风冲锋衣
- 西装外套长裤两件套
- 短袖上衣短裤两件套
- 运动上衣紧身裤套装

不得只写“衣服”“外套”“套装”“上衣”等宽泛品类。

2. 适用性别  
明确写出“男士”“女士”或“中性”。

3. 版型  
根据轮廓写出“修身版型”“常规版型”或“宽松版型”。无法确认时使用“常规版型”，不得使用“显瘦”等主观词。

4. 基础结构  
根据图片写出领型、袖长、门襟、帽型、裤型、衣长或上下装组合等必要结构。

5. 可信功能  
只保留图片、功能标识或原标题能够可靠证明的功能。没有充分证据时直接省略，不得强行补充。

【德法站翻译适配规则】

1. 使用标准、客观、单义的中文服装术语。
2. 每个属性短语必须能够独立翻译，不使用依赖中文语境的省略表达。
3. 避免成语、网络用语、中文营销惯用语及含义模糊的四字词。
4. 避免重复表达相同属性，例如不得同时使用“全拉链”和“拉链开衫”描述同一结构。
5. 品类、性别和版型应相邻，避免翻译后修饰对象不清。
6. 数量型结构必须明确，例如“双侧拉链口袋”“三件式组合”“上衣长裤两件套”。
7. 品牌和型号只有在原标题中明确出现时才能保留，必须保持原始拼写，不翻译、不改写。
8. 不得添加未经证实的认证、性能等级、适用温度、专业运动用途或环保声明。
9. 不得为了堆关键词加入与商品不匹配的场景、季节、人群或风格。

【颜色与图案】

禁止出现任何具体颜色名称，包括但不限于：

红色 蓝色 绿色 黑色 白色 灰色 卡其色 米色 棕色 紫色 粉色

允许描述不涉及色相的视觉类型，例如：

纯色 迷彩印花 条纹拼接 格纹 波点 字母印花 骷髅印花 花卉印花 抽象几何 撞色拼接

原标题中的具体颜色也必须删除。

【禁止用词】

严禁使用以下主观、营销化或时效性表达：

爆款 时尚 气质 新款 经典 百搭 高端 高级 奢华 潮流 必备 热卖 超值 优质 舒适 显瘦 完美 最佳

【推荐标题结构】

差异化细节1 差异化细节2 差异化细节3 核心品类 适用性别 版型 基础结构 可信功能 适用场景 品牌型号

允许根据语义调整顺序，但必须满足：

- 至少3个差异化细节位于标题开头
- 核心品类位于标题前半部分
- 性别、版型和品类完整保留
- 相同信息不得重复

【长度要求】

- 建议由8至14个属性短语组成
- 中文总长度控制在45至80个汉字
- 优先保留品类、差异化结构和高价值属性
- 信息过多时删除泛化场景词，不得删除核心品类

【输出前内部检查】

请在内部检查以下项目，但不要输出检查过程：

- 是否包含至少3个可见差异化细节
- 是否包含明确的核心品类
- 是否包含性别和版型
- 是否出现具体颜色
- 是否包含无证据的功能
- 是否包含营销词
- 是否存在重复属性
- 是否能够自然翻译为德语和法语

【输出格式】

只输出一行优化后的中文标题。

所有属性短语之间使用单个空格分隔。

不得使用逗号、顿号、冒号、括号、斜杠、加号或其他标点。

绝对不得输出分析、解释、标签、前缀、备注或额外文字。"""


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
