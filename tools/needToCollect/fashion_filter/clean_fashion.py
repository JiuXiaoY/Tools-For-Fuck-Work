"""热词清洗:只保留服装相关词 + 可形容服装的属性词(独立程序,不影响采集程序)。

思路
----
- 三个词根表(UTF-8,每行一个,# 开头为注释),与脚本同目录:
    fashion_categories.txt   服装品类词根   → 命中必保留,备注 [品类]
    fashion_attributes.txt   服装属性词根   → 命中保留,备注 [属性](防晒/功能/版型/材质/场景等)
    fashion_excludes.txt     黑名单词根     → 命中丢弃(明确的非服装噪声)
- 匹配方式:词转小写后子串匹配,兼容德语复合词(Steppjacke 命中 jacke)。
- 优先级:黑名单 > 品类 > 属性。
- 策略:先尽量保留(子串匹配 + 属性词默认也保留),每条打备注说明命中原因,
  便于人工核对、把误报词补进黑名单或从词根表剔除。
- 输出:本目录 result/hotwords_fashion_{日期}.txt,每行 词<TAB>涨幅<TAB>备注,
  仍按涨幅降序。

用法
----
    python tools/needToCollect/fashion_filter/clean_fashion.py              # 清洗最新采集文件
    python tools/needToCollect/fashion_filter/clean_fashion.py --input 某文件 --out 某文件
    python tools/needToCollect/fashion_filter/clean_fashion.py --no-attributes  # 不保留纯属性词(只留品类词)
    python tools/needToCollect/fashion_filter/clean_fashion.py --no-excludes    # 不启用黑名单(全量保留+备注)
    python tools/needToCollect/fashion_filter/clean_fashion.py --plain          # 只输出词,不带涨幅和备注
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root in sys.path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from services.logger import get_logger

# Fix Windows console encoding for German characters (ß, Ü, etc.)
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent          # tools/needToCollect/fashion_filter
SRC_DIR = BASE_DIR / "raw"                          # 采集原始数据目录(主程序 hotwords_fashion.py 的产物)
OUT_DIR = BASE_DIR / "result"                       # 本清洗工具的独立输出目录

CAT_FILE = BASE_DIR / "fashion_categories.txt"
ATTR_FILE = BASE_DIR / "fashion_attributes.txt"
EXCL_FILE = BASE_DIR / "fashion_excludes.txt"
BRAND_FILE = BASE_DIR / "fashion_brands.txt"   # 品牌/商标表(token 级移除)

_log = get_logger("clean_fashion")


# ── 词根表加载 ─────────────────────────────────────────────────────

def load_roots(path: Path) -> list[str]:
    """读词根表:每行一个,跳过空行与 # 注释行。"""
    if not path.exists():
        _log.warning("词根表不存在: %s", path)
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    roots = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        roots.append(line.lower())
    return roots


def load_attr_roots(path: Path) -> tuple[list[str], list[str]]:
    """读属性词根表,按 ! 前缀分级:返回 (强属性, 弱属性)。

    强属性(! 前缀):可独立保留(材质/防晒/功能,单独出现也有价值)。
    弱属性(无前缀):必须与服装品类词同现才保留,单独出现丢弃(防误报)。
    """
    if not path.exists():
        _log.warning("词根表不存在: %s", path)
        return [], []
    strong: list[str] = []
    weak: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("!"):
            strong.append(line[1:].strip().lower())
        else:
            weak.append(line.lower())
    return strong, weak


def strip_brands(word: str, brand_roots: list[str]) -> tuple[str, list[str]]:
    """从词中移除品牌/商标(token 级匹配),返回 (剩余部分, 移除的品牌列表)。

    - 品牌可能在词的开头/中间/结尾,可能是多个单词(如 helly hansen)。
    - 多词品牌按"词数多→少"优先匹配短语;单品牌按独立 token 匹配。
    - 大小写不敏感;输出保留原词其余 token 的大小写。
    """
    tokens = word.split()
    if not tokens:
        return word, []
    lower = [t.lower() for t in tokens]
    keep = [True] * len(tokens)
    removed: list[str] = []

    # 多词品牌:按 token 数降序,短语匹配
    multi = sorted((b for b in brand_roots if " " in b), key=lambda b: b.count(" "), reverse=True)
    for brand in multi:
        bt = brand.split()
        n = len(bt)
        for i in range(len(tokens) - n + 1):
            if keep[i] and lower[i : i + n] == bt:
                for j in range(i, i + n):
                    keep[j] = False
                removed.append(brand)

    # 单品牌:独立 token 匹配
    single = {b for b in brand_roots if " " not in b}
    for i, t in enumerate(lower):
        if keep[i] and t in single:
            keep[i] = False
            removed.append(tokens[i])

    # 去重(保序)
    seen: set[str] = set()
    removed_uniq = [b for b in removed if not (b in seen or seen.add(b))]
    stripped = " ".join(t for i, t in enumerate(tokens) if keep[i]).strip()
    return stripped, removed_uniq


def latest_input() -> Path:
    """默认输入:上一级 result_fluct/ 下最新的 hotwords_*.txt(排除清洗产物 hotwords_fashion_*)。"""
    files = sorted(
        (p for p in SRC_DIR.glob("hotwords_*.txt") if "fashion" not in p.name),
        key=lambda p: p.stat().st_mtime,
    )
    if not files:
        _log.error("%s/ 下没有 hotwords_*.txt,请先运行 hotwords_fluct_desc.py 采集", SRC_DIR)
        sys.exit(1)
    return files[-1]


def read_pairs(path: Path) -> list[tuple[str, int]]:
    """读采集结果:每行 词<TAB>涨幅;兼容纯词行(涨幅取 0)。"""
    pairs: list[tuple[str, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        word = parts[0].strip()
        fluc = _int_or_zero(parts[1]) if len(parts) > 1 else 0
        if word:
            pairs.append((word, fluc))
    return pairs


def _int_or_zero(val: object) -> int:
    try:
        return int(val)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


# ── 清洗判定 ───────────────────────────────────────────────────────

def clean_pairs(
    pairs: list[tuple[str, int]],
    cat_roots: list[str],
    strong_attrs: list[str],
    weak_attrs: list[str],
    excl_roots: list[str],
    brand_roots: list[str],
    keep_attributes: bool,
    use_excludes: bool,
) -> tuple[list[tuple[str, int, str]], dict[str, int]]:
    """逐词判定,返回 (保留项[词,涨幅,备注], 统计)。

    流程: 黑名单 → 品牌移除(token 级,去任意位置/多词品牌) → 品类词根(必保留)
          → 强属性(可独立保留,开关控制) → 弱属性单独出现丢弃(防误报)。
    备注格式: 品类:jacke;属性:wasserdicht;去品牌:adidas
    """
    kept: list[tuple[str, int, str]] = []
    stats = {"cat": 0, "attr": 0, "excluded": 0, "irrelevant": 0}

    for word, fluc in pairs:
        w = word.lower()

        # 1) 黑名单(明确非服装噪声)→ 丢弃
        if use_excludes and any(root in w for root in excl_roots):
            stats["excluded"] += 1
            continue

        # 2) 品牌移除:品牌可能在词的开头/中间/结尾,可能是多个单词
        stripped, brands = strip_brands(word, brand_roots)
        s = stripped.lower()
        brand_note = f"去品牌:{','.join(brands)}" if brands else ""

        # 3) 品类词根 → 必保留(强/弱属性作为备注补充)
        cats = [r for r in cat_roots if r in s]
        if cats:
            note = "品类:" + ",".join(cats)
            attrs = [r for r in strong_attrs if r in s] + [r for r in weak_attrs if r in s]
            if attrs:
                note += ";属性:" + ",".join(attrs)
            if brand_note:
                note += ";" + brand_note
            kept.append((stripped, fluc, note))
            stats["cat"] += 1
            continue

        # 4) 强属性 → 可独立保留(开关控制);弱属性单独出现 → 丢弃(防误报)
        if keep_attributes:
            sattrs = [r for r in strong_attrs if r in s]
            if sattrs:
                note = "属性:" + ",".join(sattrs)
                if brand_note:
                    note += ";" + brand_note
                kept.append((stripped, fluc, note))
                stats["attr"] += 1
                continue

        # 5) 未命中任何规则 → 丢弃
        stats["irrelevant"] += 1

    return kept, stats


def save_result(kept: list[tuple[str, int, str]], out_path: Path, plain: bool) -> None:
    """写输出:词<TAB>涨幅<TAB>备注(plain 时只写词)。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if plain:
        lines = [w for w, _f, _n in kept]
    else:
        lines = [f"{w}\t{f}\t{n}" for w, f, n in kept]
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ── main ───────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="热词清洗:只保留服装相关词 + 可形容服装的属性词,保留项打备注"
    )
    parser.add_argument("--input", default="", help="采集结果文件(默认 result_fluct/ 最新 hotwords_*.txt)")
    parser.add_argument("--out", default="", help="输出文件(默认 result_fluct/hotwords_fashion_{日期}.txt)")
    parser.add_argument("--keep-attributes", dest="keep_attributes", action="store_true",
                        default=True, help="保留纯属性词(默认开)")
    parser.add_argument("--no-attributes", dest="keep_attributes", action="store_false",
                        help="关闭:纯属性词(未命中品类)也丢弃,只留服装品类词")
    parser.add_argument("--excludes", dest="use_excludes", action="store_true",
                        default=True, help="启用黑名单(默认开)")
    parser.add_argument("--no-excludes", dest="use_excludes", action="store_false",
                        help="关闭:不启用黑名单,所有词先打备注再按品类/属性判断")
    parser.add_argument("--plain", action="store_true", help="只输出词,不带涨幅和备注")
    args = parser.parse_args()

    # 词根表
    cat_roots = load_roots(CAT_FILE)
    strong_attrs, weak_attrs = load_attr_roots(ATTR_FILE)
    excl_roots = load_roots(EXCL_FILE)
    brand_roots = load_roots(BRAND_FILE)
    _log.info("词根表: 品类 %d / 强属性 %d / 弱属性 %d / 黑名单 %d / 品牌 %d",
              len(cat_roots), len(strong_attrs), len(weak_attrs), len(excl_roots), len(brand_roots))

    # 输入输出
    in_path = Path(args.input) if args.input else latest_input()
    date_str = datetime.now().strftime("%Y%m%d")
    out_path = Path(args.out) if args.out else OUT_DIR / f"hotwords_fashion_{date_str}.txt"

    pairs = read_pairs(in_path)
    _log.info("输入: %s (%d 条)", in_path.name, len(pairs))
    if not pairs:
        _log.info("输入为空,退出。")
        return

    # 清洗
    kept, stats = clean_pairs(
        pairs, cat_roots, strong_attrs, weak_attrs, excl_roots, brand_roots,
        keep_attributes=args.keep_attributes, use_excludes=args.use_excludes,
    )
    kept.sort(key=lambda item: item[1], reverse=True)  # 仍按涨幅降序

    # 保存
    save_result(kept, out_path, args.plain)

    # 报告
    total = len(pairs)
    kept_n = len(kept)
    _log.info("")
    _log.info("=== 清洗报告 ===")
    _log.info("保留: %d (品类 %d / 属性 %d)", kept_n, stats["cat"], stats["attr"])
    _log.info("丢弃: %d (黑名单 %d / 无关 %d)", total - kept_n, stats["excluded"], stats["irrelevant"])
    _log.info("输出: %s", out_path)
    if kept:
        _log.info("")
        _log.info("保留示例(Top15):")
        for w, f, n in kept[:15]:
            _log.info("  %s\t%d\t%s", w, f, n)


if __name__ == "__main__":
    main()
