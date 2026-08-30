# -*- coding: utf-8 -*-
"""
ai_pick_attributes —— 对「有可选值的未覆盖列」用 **DeepSeek 网页版** 一次询问 AI 选值，
更新 M 数据源 JSON。

按 MISSING.md 的解决方案（类似 tools/title_optimize/deepseek_web.py 的网页自动化方式）：
  - 未覆盖列中，completed.json 有可选值(choices)的列（如 17/126 领型、141 袖型、143 闭合）
    → **一次对话问完所有列**：提示词里含 产品列表 + 每列的可选值，AI 按列分块输出，
    每个产品每列选出 1 个值；
  - 每列每组只存 1 个值 → fill_from_plan 以 cycle 模式循环铺满整组；
  - 无可选值的列保持 dataTemp 占位不变。

产物文件（ai_prompt/ 下只有 2 个）：
  - attributes_all.txt          一次合并的提示词
  - attributes_all_result.txt   AI 回答（存在则复用，跳过网页）

只有网页版（无 API）：playwright 打开 DeepSeek 网页发送提示词，读取回答解析写回。
登录态保存在 antelope/web_data/ + .deepseek_state.json（首次弹浏览器手动登录一次）。

用法:
    python antelope/ai_pick_attributes.py                          # 网页自动化 + 写回
    python antelope/ai_pick_attributes.py --products-file products.txt   # 用指定产品列表
    python antelope/ai_pick_attributes.py --generate-only          # 只生成提示词文件，不发网页
    python antelope/ai_pick_attributes.py --source-excel x --m-data y
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import openpyxl

from common import (
    load_ai_columns,
    load_groups,
    load_json,
    setup_utf8,
    uncovered_cols,
    zcfg,
)

BASE = Path(__file__).resolve().parent

DEFAULT_DIFF = zcfg.CFG_INTERMEDIATE["column_diff_json"]
DEFAULT_COMPLETED = zcfg.CFG_INTERMEDIATE["completed_json"]
DEFAULT_GROUPS = zcfg.CFG_INTERMEDIATE["groups_json"]
DEFAULT_DATA = zcfg.CFG_INTERMEDIATE["data_json"]
DEFAULT_SOURCE_EXCEL = zcfg.DATA_SOURCE_A
DEFAULT_M_DATA = zcfg.DATA_SOURCE_M
DEFAULT_PROMPT_DIR = zcfg.CFG_INTERMEDIATE["ai_prompt_dir"]

# 产品描述取数据源 A(Sheet0) 的这些列：I(9)=中文标题（产品列表展示用中文）
PRODUCT_DESC_COLS = (9,)

# ── DeepSeek 网页自动化 ──
DEEPSEEK_URL = "https://chat.deepseek.com/"
WEB_DATA_DIR = BASE / "web_data"            # 浏览器数据（登录态持久化）
STATE_FILE = BASE / ".deepseek_state.json"  # 登录态快照（复用）
ASSISTANT_SEL = "div.ds-assistant-message-main-content"

# ai_prompt 下固定 2 个文件：合并提示词 + 合并结果
PROMPT_ALL_NAME = "attributes_all.txt"
RESULT_ALL_NAME = "attributes_all_result.txt"

# 法文表头 → 中文短标签（提示词里不显示列号，程序内部维护 col ↔ 标签 映射）
HEADER_LABELS = {
    "Style de col": "领型",
    "Type de manches": "袖型",
    "Type de fermeture": "闭合",
}


def make_labels(ai_cols) -> dict[int, str]:
    """给每列分配简短中文标签；同名表头自动加序号（如 领型 / 领型2）。"""
    used: dict[str, int] = {}
    labels: dict[int, str] = {}
    for col, header, _ in ai_cols:
        base = HEADER_LABELS.get(header, header)
        n = used.get(base, 0) + 1
        used[base] = n
        labels[col] = f"{base}{n}" if n > 1 else base
    return labels


def build_product_list_from_excel(source_excel, groups):
    """从数据源 A(Sheet0) 提取产品列表：每组取锚点行（组起始行）的 标题|卖点。"""
    wb = openpyxl.load_workbook(source_excel, read_only=True, data_only=True)
    try:
        ws = wb[wb.sheetnames[0]]  # 规则：只读第一个工作表（Sheet0）
        products = []
        for gname, spec in (groups or {}).items():
            spec = str(spec).strip()
            if "&" not in spec:
                continue
            try:
                start_actual, _ = map(int, spec.split("&"))
            except ValueError:
                continue
            parts = []
            for c in PRODUCT_DESC_COLS:
                v = ws.cell(row=start_actual, column=c).value
                if v is not None and str(v).strip():
                    parts.append(str(v).strip())
            products.append(" | ".join(parts) if parts else f"({gname})")
        return products
    finally:
        wb.close()


def load_products_from_file(path):
    """从文本文件读取产品列表（每行一个产品）。"""
    return [l.strip() for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def build_prompt_all(products, ai_cols, labels):
    """构造一次合并的提示词：产品列表 + 各组可选值（编号形式，AI 输出编号杜绝造词）。"""
    lines = [
        "请为以下每个产品，从各组可选值中选出最合适的 1 个值。",
        "",
        "【规则】",
        "1. 每个值都必须是该组「可选值」列表中的原词；若没有完全匹配的值，请在**该组列表内**选择语义上最接近、最合适的一个。",
        "2. 为方便你作答，可选值已编号；**输出时直接给出选项编号（数字）**，不要输出文字值，不要造词。",
        "",
        "【产品列表】（每组一个产品，编号 1~N）：",
    ]
    for i, p in enumerate(products, 1):
        lines.append(f"{i}. {p}")
    lines += [
        "",
        "【可选值组】（每组只能从该组编号中选择）：",
    ]
    for col, header, choices in ai_cols:
        numbered = ", ".join(f"{i}.{c}" for i, c in enumerate(choices, 1))
        lines.append(f"{labels[col]}: {numbered}")
    lines += [
        "",
        "【输出格式】按组名分块输出，每块内每行一个产品（产品编号+冒号+选项编号），不要任何解释：",
        f"{labels[ai_cols[0][0]]}:",
        "1: <选项编号>",
        "2: <选项编号>",
        "...",
    ]
    return "\n".join(lines)


_LINE_RE = re.compile(r"^\s*(\d+)\s*[:：]\s*(.+?)\s*$")


def parse_all(text, ai_cols, n_products, labels):
    """解析一次合并回答 → {col: {产品编号: 值}}。

    值支持两种形态：
      - 数字（推荐，提示词要求输出选项编号）→ 映射回该列可选值；
      - 文字 → 严格匹配该列可选值（大小写/变体归一化）。
    非法值（编号越界 / 文字不在可选值内）→ 拒绝并警告，该产品保持占位。
    """
    choices_by_col = {col: [str(c) for c in choices] for col, _, choices in ai_cols}
    norm = {col: {str(c).strip().casefold(): str(c).strip() for c in choices}
            for col, _, choices in ai_cols}
    label_to_col = {labels[col]: col for col, _, _ in ai_cols}
    result: dict[int, dict[int, str]] = {}
    rejected: list[tuple[int, str]] = []   # (col, 被拒值)

    cur_col = None
    for raw in str(text or "").splitlines():
        line = raw.strip().rstrip(":：").strip()
        if not line:
            continue
        if line in label_to_col:          # 块头（短标签）
            cur_col = label_to_col[line]
            continue
        if cur_col is None:
            continue
        ml = _LINE_RE.match(line)
        if not ml:
            continue
        no = int(ml.group(1))
        val = ml.group(2).strip()
        if not (1 <= no <= n_products and val):
            continue

        # 形态 1：选项编号
        if val.isdigit():
            idx = int(val)
            opts = choices_by_col.get(cur_col, [])
            if 1 <= idx <= len(opts):
                result.setdefault(cur_col, {})[no] = opts[idx - 1]
            else:
                rejected.append((cur_col, val))
            continue

        # 形态 2：文字，严格匹配可选值
        matched = norm.get(cur_col, {}).get(val.casefold())
        if matched is None:
            rejected.append((cur_col, val))
            continue
        result.setdefault(cur_col, {})[no] = matched

    if rejected:
        print(f"  ⚠️ 拒绝 {len(rejected)} 个不在可选值内的值（保持占位）: {rejected}")
    return result


def update_m_data(m_data, groups, col, parsed, placeholder):
    """把 AI 选值写入 M 数据（每组 1 个值 → cycle 铺满）。

    该列该组没有合法值（缺失/被拒）→ **覆盖为占位**（不留旧值残留）。
    """
    updated = 0
    kept = 0
    for i, (gname, spec) in enumerate((groups or {}).items(), 1):
        if str(spec).strip().count("&") != 1:
            continue
        gdata = m_data.setdefault(str(gname), {})
        val = parsed.get(i)
        if val:
            gdata[str(col)] = [val]          # 单元素 → fill_from_plan cycle 铺满
            updated += 1
        else:
            gdata[str(col)] = [placeholder]  # 覆盖为占位，防止旧值残留
            kept += 1
    return updated, kept


# ══════════════════════════════════════════════════════════════════════════
#  DeepSeek 网页自动化（参考 tools/title_optimize/deepseek_web.py）
# ══════════════════════════════════════════════════════════════════════════
def last_assistant_text(page) -> str:
    """页面上最后一条助手回复文本（发送前记录基线用）。"""
    locator = page.locator(ASSISTANT_SEL)
    texts = []
    for m in locator.all():
        try:
            t = m.inner_text().strip()
        except Exception:
            continue
        if t:
            texts.append(t)
    return texts[-1] if texts else ""


def extract_last_response(page, previous_text: str = "", timeout: int = 300) -> str:
    """等待生成结束并提取最后一条助手回复（排除思考过程；新文本连续 3 秒无变化判定完成）。"""
    locator = page.locator(ASSISTANT_SEL)
    stop_btn = page.locator("button:has-text('Stop')")
    deadline = time.monotonic() + timeout
    last_text, stable = "", 0
    while time.monotonic() < deadline:
        texts = []
        for m in locator.all():
            try:
                t = m.inner_text().strip()
            except Exception:
                continue
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


def web_ask_all(ai_cols, products, args, m_data, groups):
    """用 DeepSeek 网页一次对话询问所有列，解析后更新 M JSON。"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("❌ playwright 未安装。请先执行：")
        print("    pip install playwright")
        print("    playwright install chromium")
        sys.exit(3)

    os.makedirs(args.prompt_dir, exist_ok=True)
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    labels = make_labels(ai_cols)
    prompt = build_prompt_all(products, ai_cols, labels)
    p_path = os.path.join(args.prompt_dir, PROMPT_ALL_NAME)
    r_path = os.path.join(args.prompt_dir, RESULT_ALL_NAME)
    Path(p_path).write_text(prompt, encoding="utf-8")
    print(f"合并提示词已生成: {p_path}（标签: {labels}）")

    # 已有 result → 直接复用，跳过网页
    if os.path.exists(r_path):
        text = Path(r_path).read_text(encoding="utf-8")
        parsed = parse_all(text, ai_cols, len(products), labels)
        print(f"复用已有回答，解析到列: {sorted(parsed)}")
        for col, _, _ in ai_cols:
            updated, kept = update_m_data(m_data, groups, col, parsed.get(col, {}), args.placeholder)
            print(f"  列{col}: 更新 {updated} 组，保留占位 {kept} 组")
        return

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(WEB_DATA_DIR),
            headless=False,
        )
        page = context.new_page()
        page.goto(DEEPSEEK_URL, wait_until="domcontentloaded")
        print(f"已打开 {DEEPSEEK_URL}")

        if not STATE_FILE.exists():
            print("=" * 60)
            print("首次运行：请在弹出的浏览器中登录 DeepSeek")
            print("登录完成后程序会自动继续（最多等待 10 分钟）...")
            print("=" * 60)
            logged_in = False
            for _ in range(600):
                try:
                    if page.locator("textarea, [contenteditable]").count() > 0:
                        logged_in = True
                        break
                except Exception:
                    pass
                time.sleep(1)
            if not logged_in:
                raise RuntimeError("等待登录超时（10 分钟），请确认浏览器中已登录 DeepSeek")
            time.sleep(2)
            context.storage_state(path=str(STATE_FILE))
            print(f"登录态已保存: {STATE_FILE.name}")
        else:
            print(f"复用登录态: {STATE_FILE.name}")

        page.wait_for_selector("textarea, [contenteditable]", timeout=30000)
        time.sleep(2)
        print("DeepSeek 对话页就绪")

        new_chat_btn = page.locator("text=New Chat").first
        if new_chat_btn.is_visible():
            new_chat_btn.click()
            time.sleep(1)

        textarea = page.locator("textarea").first
        textarea.fill(prompt)
        time.sleep(1)

        prev_text = last_assistant_text(page)
        page.keyboard.press("Enter")
        print("已发送（一次询问所有列），等待 AI 回答...")
        time.sleep(15)

        answer = extract_last_response(page, previous_text=prev_text)
        Path(r_path).write_text(answer, encoding="utf-8")
        print(f"回答已保存: {r_path}")

        context.close()

    parsed = parse_all(answer, ai_cols, len(products), labels)
    print(f"解析到列: {sorted(parsed)}")
    for col, _, _ in ai_cols:
        updated, kept = update_m_data(m_data, groups, col, parsed.get(col, {}), args.placeholder)
        print(f"  列{col}: 更新 {updated} 组，保留占位 {kept} 组")


def main():
    parser = argparse.ArgumentParser(
        description="对「有可选值的未覆盖列」用 DeepSeek 网页版一次询问 AI 选值，更新 M 数据源 JSON"
    )
    parser.add_argument("--diff", default=DEFAULT_DIFF, help="column_diff JSON 路径")
    parser.add_argument("--completed", default=DEFAULT_COMPLETED, help="completed 分析 JSON 路径")
    parser.add_argument("--groups", default=DEFAULT_GROUPS, help="groups JSON 路径")
    parser.add_argument("--data", default=DEFAULT_DATA, help="A 取数 data JSON 路径（判断已覆盖列）")
    parser.add_argument("--source-excel", default=DEFAULT_SOURCE_EXCEL, help="数据源 A(.xlsx)，无 --products-file 时用它提取产品列表")
    parser.add_argument("--products-file", default=None, help="产品列表文件（每行一个产品）；缺省从数据源 A 提取")
    parser.add_argument("--m-data", default=DEFAULT_M_DATA, help="M JSON 路径（读占位/写结果）")
    parser.add_argument("--prompt-dir", default=DEFAULT_PROMPT_DIR, help="提示词/结果文件目录（只放 2 个文件）")
    parser.add_argument("--placeholder", default="dataTemp", help="占位值")
    parser.add_argument("--generate-only", action="store_true",
                        help="只生成合并提示词文件，不打开网页（手动喂 AI，回答存 result 文件后重跑写回）")
    args = parser.parse_args()

    setup_utf8()

    groups = load_groups(args.groups)
    if not groups:
        print("⚠️ groups 为空，无法确定分组行数")
        sys.exit(1)

    ai_cols = load_ai_columns(args.completed, uncovered_cols(args.diff, args.data))

    if not ai_cols:
        print("未覆盖列中没有找到有可选值(choices)的列，无需 AI 选值。")
        return

    # 产品列表
    if args.products_file:
        products = load_products_from_file(args.products_file)
        print(f"产品列表（文件）：{len(products)} 个")
    else:
        products = build_product_list_from_excel(args.source_excel, groups)
        print(f"产品列表（数据源 A Sheet0 提取）：{len(products)} 个")

    print(f"AI 选值列：{[c[0] for c in ai_cols]}（一次对话合并询问）")

    # 读现有 M JSON
    m_data = {}
    if os.path.exists(args.m_data):
        m_data = load_json(args.m_data).get("data") or {}

    if args.generate_only:
        os.makedirs(args.prompt_dir, exist_ok=True)
        p_path = os.path.join(args.prompt_dir, PROMPT_ALL_NAME)
        labels = make_labels(ai_cols)
        Path(p_path).write_text(build_prompt_all(products, ai_cols, labels), encoding="utf-8")
        print(f"合并提示词已生成: {p_path}（标签: {labels}）")
        return

    web_ask_all(ai_cols, products, args, m_data, groups)

    # 写回 M JSON
    with open(args.m_data, "w", encoding="utf-8") as f:
        json.dump({"data": m_data, "placeholder": args.placeholder}, f, ensure_ascii=False, indent=2)
    print(f"\nM 数据源已更新: {args.m_data}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
