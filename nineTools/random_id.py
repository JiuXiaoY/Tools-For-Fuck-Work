"""独立的随机 ID 生成小工具。

规则与流水线 steps/assign_ids.py 中生成的随机 ID 完全一致：
    <前6位><中间6位日期码><后4位>  →  共 16 位
    - 前/后位字符集: 大小写字母 + 数字 (base62)
    - 中间 6 位日期码: YYMMDD 按 digit→letter 映射 (0→z,1→a,2→b,...,9→i)

独立小工具，不依赖流水线代码，所有配置集中在本文件顶部 SETTINGS 中完成。
运行:  python random_id.py
       python random_id.py --count 20
"""

from __future__ import annotations

import argparse
import secrets
import string
import sys
from datetime import date
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────
#  配置区（所有配置在此完成）
# ─────────────────────────────────────────────────────────────────────
SETTINGS = {
    "count": 1549,                  # 生成数量
    "date_override": "260814",          # 固定日期码 (格式 YYMMDD，如 "260702")；留空则用今天
    "prefix_len": 6,              # 前段随机字符数
    "middle_len": 6,              # 中间日期码长度（通常 6，勿改）
    "suffix_len": 4,              # 后段随机字符数
    "charset": string.digits + string.ascii_uppercase + string.ascii_lowercase,  # 随机字符集
    "print_id": True,             # 是否在控制台输出
    "save_file": "",              # 输出文件路径（留空则不写文件）
}

# digit → letter 映射：0→z, 1→a, ..., 9→i（与流水线一致）
_DIGIT_MAP = dict(zip("0123456789", "zabcdefghi"))


def _date_code(yymmdd: str = "") -> str:
    """生成 6 位日期码；指定 yymmdd 则用之，否则用今天日期。"""
    if yymmdd.strip():
        raw = yymmdd.strip()
    else:
        today = date.today()
        raw = f"{today.year % 100:02d}{today.month:02d}{today.day:02d}"
    return "".join(_DIGIT_MAP[d] for d in raw)


def generate_one(s: dict) -> str:
    """按配置生成一条随机 ID。"""
    prefix = "".join(secrets.choice(s["charset"]) for _ in range(s["prefix_len"]))
    middle = _date_code(s["date_override"])
    suffix = "".join(secrets.choice(s["charset"]) for _ in range(s["suffix_len"]))
    return f"{prefix}{middle}{suffix}"


def main() -> None:
    parser = argparse.ArgumentParser(description="生成随机 ID（规则同流水线 assign_ids）")
    parser.add_argument("--count", type=int, default=SETTINGS["count"],
                        help=f"生成数量 (默认 {SETTINGS['count']})")
    args = parser.parse_args()

    s = dict(SETTINGS)
    s["count"] = max(1, args.count)

    # 生成 count 条，保证不重复（概率碰撞时自动重试补齐）
    ids: list[str] = []
    seen: set[str] = set()
    _guard = 0
    while len(ids) < s["count"] and _guard < s["count"] * 100:
        rid = generate_one(s)
        _guard += 1
        if rid in seen:
            continue          # 重复则重新生成
        seen.add(rid)
        ids.append(rid)
    expected_len = s["prefix_len"] + s["middle_len"] + s["suffix_len"]

    # 输出目标：条数 >100 → 自动落盘；否则按配置（控制台/文件）
    if s["count"] > 100:
        s["print_id"] = False   # 太多时不刷屏
        if not s["save_file"]:
            # 自命名：YYYYMMDD_HHMMSS_rand.txt（与随机 ID 同目录）
            stamp = _datetime_now()
            out_path = Path(__file__).resolve().parent / f"random_ids_{stamp}.txt"
        else:
            out_path = Path(s["save_file"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(ids) + "\n", encoding="utf-8")
        print(f"[已写入 {len(ids)} 条] {out_path.resolve()}", file=sys.stderr)
        print(f"[首条] {ids[0]}", file=sys.stderr)
        print(f"[末条] {ids[-1]}", file=sys.stderr)
    else:
        if s["print_id"]:
            for rid in ids:
                print(rid)
        if s["save_file"]:
            out = Path(s["save_file"])
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text("\n".join(ids) + "\n", encoding="utf-8")
            print(f"[已写入] {out.resolve()} ({len(ids)} 条)", file=sys.stderr)

    # 校验并提示
    if ids:
        ok = all(len(x) == expected_len for x in ids)
        print(f"[校验] 每条 {expected_len} 位，共 {len(ids)} 条 → {'通过' if ok else '异常'}", file=sys.stderr)


def _datetime_now() -> str:
    """当前时间戳 YYYYMMDD_HHMMSS，用于自命名输出文件。"""
    return date.today().strftime("%Y%m%d") + "_" + _hms_now()


def _hms_now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%H%M%S")


if __name__ == "__main__":
    main()
