"""热词采集 + 服装词清洗 一条龙(唯一入口,不影响 needToCollect/ 下现有 hotwords.py)。

流程(一次运行,无需再跑第二个程序):
    1. 采集  :不带搜索词,按涨幅降序拉取前 N 页热词(默认 5 页 × 200 条)
    2. 留存原始: raw/hotwords_{日期}.txt                词<TAB>涨幅(涨幅降序)
    3. 清洗  :只保留服装相关词 + 可形容服装的属性词,每条打备注(原因)
    4. 留存结果: result/hotwords_fashion_{日期}.txt    词<TAB>涨幅<TAB>备注

所有数据文件只保存在本目录下(raw/ 原始数据、result/ 清洗结果),不写到别处。
清洗词根表也在本目录:fashion_categories.txt / fashion_attributes.txt / fashion_excludes.txt。
清洗逻辑复用 clean_fashion.py(本目录)。

用法:
    python tools/needToCollect/fashion_filter/hotwords_fashion.py              # 默认全流程
    python tools/needToCollect/fashion_filter/hotwords_fashion.py --pages 3    # 只拉前 3 页
    python tools/needToCollect/fashion_filter/hotwords_fashion.py --top 200    # 清洗后只留涨幅前 200
    python tools/needToCollect/fashion_filter/hotwords_fashion.py --no-clean   # 只采集留 raw,不清洗
    python tools/needToCollect/fashion_filter/hotwords_fashion.py --no-attributes  # 清洗时不保留纯属性词
    python tools/needToCollect/fashion_filter/hotwords_fashion.py --no-excludes    # 清洗时不启用黑名单
    python tools/needToCollect/fashion_filter/hotwords_fashion.py --plain          # 清洗输出纯词(不带备注)
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

# Ensure project root in sys.path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

# 复用同目录 clean_fashion.py 的清洗逻辑
from clean_fashion import (
    BRAND_FILE, CAT_FILE, ATTR_FILE, EXCL_FILE,
    clean_pairs, load_attr_roots, load_roots, save_result,
)

from services.logger import get_logger

# Fix Windows console encoding for German characters (ß, Ü, etc.)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API_URL = "https://api.amz123.com/search/v1/hotwords/search"
BASE_DIR = Path(__file__).resolve().parent      # tools/needToCollect/fashion_filter
RAW_DIR = BASE_DIR / "raw"                      # 采集原始数据(清洗前)留档
RESULT_DIR = BASE_DIR / "result"                # 清洗结果(清洗后)留档

PAGE_SIZE = 200
REQUEST_INTERVAL = 2.0      # seconds between page requests
REQUEST_TIMEOUT = 30
DEFAULT_PAGES = 5           # 默认取前 5 页

_log = get_logger("hotwords_fashion")


# ── 采集 ───────────────────────────────────────────────────────────

def build_payload(country: str, category: str, page_num: int = 1) -> dict:
    """按涨幅降序请求热词 API(condition=fluctuation, order=1 升序),不带搜索词。

    API 语义: fluctuation = new_rank - old_rank,负值=热度上升(涨幅),
    正值=热度下降/新上榜。升序即最负(涨幅最大)在前。
    """
    return {
        "word": "",  # 不按搜索词过滤
        "country": country,
        "ranking_this_week": [],
        "fluctuation_range": [],
        "word_len_range": [],
        "click_range": [],
        "conversion_range": [],
        "ne_word": "",
        "top3_brand": "",
        "top3_category": category,
        "page": {
            "size": PAGE_SIZE,
            "num": page_num,
            "sorts": [{"condition": "fluctuation", "order": 1}],
        },
    }


def fetch_pairs(country: str, category: str, pages: int = DEFAULT_PAGES) -> list[tuple[str, int]]:
    """循环请求前 pages 页,返回 [(word, fluctuation), ...](未排序、未过滤)。"""
    pairs: list[tuple[str, int]] = []
    for num in range(1, pages + 1):
        resp = requests.post(
            API_URL, json=build_payload(country, category, page_num=num), timeout=REQUEST_TIMEOUT
        )
        resp.raise_for_status()
        rows = resp.json().get("data", {}).get("rows", [])
        _log.info("  第 %d/%d 页: %d 条", num, pages, len(rows))
        for row in rows:
            word = row.get("word")
            if not word or not str(word).strip():
                continue
            pairs.append((str(word).strip(), _int_or_zero(row.get("fluctuation"))))
        if len(rows) < PAGE_SIZE:
            _log.info("  已到最后一页(不足 %d 条),提前结束", PAGE_SIZE)
            break
        if num < pages:
            time.sleep(REQUEST_INTERVAL)
    return pairs


def _int_or_zero(val: object) -> int:
    try:
        return int(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def save_raw(pairs: list[tuple[str, int]], date_str: str) -> Path:
    """留存采集原始数据(清洗前):raw/hotwords_{日期}.txt,词<TAB>涨幅。

    同一天重复运行时若文件已存在,自动追加时分秒后缀,避免覆盖历史数据。
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out_path = RAW_DIR / f"hotwords_{date_str}.txt"
    if out_path.exists():
        stamp = datetime.now().strftime("%H%M%S")
        out_path = RAW_DIR / f"hotwords_{date_str}_{stamp}.txt"
    out_path.write_text("\n".join(f"{w}\t{f}" for w, f in pairs), encoding="utf-8")
    return out_path


# ── main ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="热词采集+服装词清洗一条龙(数据只存本目录 raw/ 与 result/)"
    )
    # 采集参数
    parser.add_argument("--country", default="de", help="目标站点(默认 de)")
    parser.add_argument("--category", default="", help="top3 品类过滤(可选)")
    parser.add_argument("--pages", type=int, default=DEFAULT_PAGES,
                        help=f"拉取前 N 页(默认 {DEFAULT_PAGES},每页 {PAGE_SIZE} 条)")
    parser.add_argument("--no-clean", dest="clean", action="store_false", default=True,
                        help="只采集并留存 raw/,不执行清洗")
    # 清洗参数
    parser.add_argument("--keep-attributes", dest="keep_attributes", action="store_true",
                        default=True, help="清洗时保留纯属性词(默认开)")
    parser.add_argument("--no-attributes", dest="keep_attributes", action="store_false",
                        help="清洗时不保留纯属性词,只留服装品类词")
    parser.add_argument("--excludes", dest="use_excludes", action="store_true",
                        default=True, help="清洗时启用黑名单(默认开)")
    parser.add_argument("--no-excludes", dest="use_excludes", action="store_false",
                        help="清洗时不启用黑名单")
    parser.add_argument("--top", type=int, default=0,
                        help="清洗结果只保留涨幅最大的前 N 个(0=全部)")
    parser.add_argument("--min-fluc", type=int, default=1,
                        help="清洗结果只保留涨幅 >= 此值的词(默认 1;设负值可放宽到小涨幅)")
    parser.add_argument("--keep-drop", action="store_true",
                        help="清洗结果连同降幅(负涨幅)词一起保留,排在最末")
    parser.add_argument("--plain", action="store_true",
                        help="清洗输出只写词,不带涨幅和备注")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y%m%d")
    _log.info("=== 1/2 采集: country=%s category=%s pages=%d (不带搜索词,按涨幅降序) ===",
              args.country, args.category or "(all)", args.pages)

    # ── 采集(失败自动重试,复用 hotwords 重试配置) ──
    from config import Config
    cfg = Config()
    pairs_all: list[tuple[str, int]] = []
    for attempt in range(1, cfg.retry_max_rounds_hotwords + 1):
        try:
            pairs_all = fetch_pairs(args.country, args.category, pages=args.pages)
            _log.info("第 %d 次请求成功: %d 条", attempt, len(pairs_all))
            break
        except Exception as exc:
            _log.warning("请求失败(第 %d/%d 次): %s", attempt, cfg.retry_max_rounds_hotwords, exc)
            if attempt < cfg.retry_max_rounds_hotwords:
                time.sleep(3)

    if not pairs_all:
        _log.info("未获取到任何数据。")
        return

    # ── 去重(同一词保留最高涨幅)并按涨幅降序,统一为"涨幅"正数视角(涨幅=-fluctuation) ──
    fluc_map: dict[str, int] = {}
    for w, f in pairs_all:
        key = w.lower()
        fluc_map[key] = max(fluc_map.get(key, f), f)
    pairs = sorted(((w, -f) for w, f in fluc_map.items()), key=lambda p: p[1], reverse=True)

    # ── 留存原始(清洗前) ──
    raw_path = save_raw(pairs, date_str)
    _log.info("原始数据已留存(清洗前): %s (%d 条)", raw_path.name, len(pairs))

    if not args.clean:
        _log.info("--no-clean 指定,跳过清洗。")
        return

    # ── 清洗 ──
    _log.info("=== 2/2 清洗: 品类词根+属性词根(强弱)+黑名单+品牌表 ===")
    cat_roots = load_roots(CAT_FILE)
    strong_attrs, weak_attrs = load_attr_roots(ATTR_FILE)
    excl_roots = load_roots(EXCL_FILE)
    brand_roots = load_roots(BRAND_FILE)
    _log.info("词根表: 品类 %d / 强属性 %d / 弱属性 %d / 黑名单 %d / 品牌 %d",
              len(cat_roots), len(strong_attrs), len(weak_attrs), len(excl_roots), len(brand_roots))

    kept, stats = clean_pairs(
        pairs, cat_roots, strong_attrs, weak_attrs, excl_roots, brand_roots,
        keep_attributes=args.keep_attributes, use_excludes=args.use_excludes,
    )
    # 涨幅过滤(keep-drop 时降幅词涨幅为负,排在末位)
    kept.sort(key=lambda item: item[1], reverse=True)
    if not args.keep_drop:
        kept = [k for k in kept if k[1] >= args.min_fluc]
    if args.top > 0:
        kept = kept[: args.top]

    # ── 留存清洗结果(同日重复运行自动加时间戳后缀,防覆盖) ──
    out_path = RESULT_DIR / f"hotwords_fashion_{date_str}.txt"
    if out_path.exists():
        stamp = datetime.now().strftime("%H%M%S")
        out_path = RESULT_DIR / f"hotwords_fashion_{date_str}_{stamp}.txt"
    save_result(kept, out_path, args.plain)

    # ── 报告 ──
    total = len(pairs)
    _log.info("")
    _log.info("=== 报告 ===")
    _log.info("采集原始: %d 条 → raw/%s", total, raw_path.name)
    _log.info("清洗命中: 品类 %d / 属性 %d(过滤前)", stats["cat"], stats["attr"])
    _log.info("清洗丢弃: %d 条(黑名单 %d / 无关 %d)",
              stats["excluded"] + stats["irrelevant"], stats["excluded"], stats["irrelevant"])
    _log.info("最终保留: %d 条(经 --top/--min-fluc/--keep-drop 过滤)", len(kept))
    _log.info("结果文件: result/%s", out_path.name)
    if kept:
        _log.info("保留示例(Top10):")
        for w, f, n in kept[:10]:
            _log.info("  %s\t%d\t%s", w, f, n)


if __name__ == "__main__":
    main()
