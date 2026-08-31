# -*- coding: utf-8 -*-
"""
color_change & size_change 是原始数据根据 dealExcel_refactoring/data/color_mapping_de.json
dealExcel_refactoring/data/size_mapping_de.json 得出的结果
我想转变为 根据 dealExcel_refactoring/data/size_mapping_fr.json
dealExcel_refactoring/data/color_mapping_fr.json 映射的结果
在此处写个单独程序 实现 德 -> 原始数据 -> 法 转换 , 产出直接覆盖原数据文件 数据即可, 碰到数字或者全大写的 保持不变即可 比如 08 Weiß ，08 保持，后面的转换

实现说明：
  1. 四个映射文件都是「原始英文 -> 目标语言」：
       color_mapping_de.json / size_mapping_de.json  = 原始 -> 德
       color_mapping_fr.json / size_mapping_fr.json  = 原始 -> 法
  2. 转换管线：德文值 -> (反查 de 映射得到原始英文) -> (查 fr 映射得到法文)。
  3. 规则：
       - 整值精确反查命中 → 直接转法文（如 "Schwarz" -> "Noir"、"L (l)" -> "Grand (l)"）；
       - 未命中时若形如 "数字 颜色词"（如 "08 Weiß"、"01 Schwarz"），数字前缀保留，
         剩余部分递归转换（"08 Weiß" -> "08 Blanc"）；
       - 其余（数字 / 全大写代码，如 "60"、"XXL/42"、"68X84.5CM"、"10Y"、"14Y"、"6Y"）保持原样。
  4. 只覆盖 nineTools/color_change 与 nineTools/size_change 两个文件；
     保留空行与 CRLF 行尾（文件本身无末尾换行，写回时保持一致）。
"""

import json
import os
import re
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "..", "data")

COLOR_DE = os.path.join(DATA_DIR, "color_mapping_de.json")
COLOR_FR = os.path.join(DATA_DIR, "color_mapping_fr.json")
SIZE_DE = os.path.join(DATA_DIR, "size_mapping_de.json")
SIZE_FR = os.path.join(DATA_DIR, "size_mapping_fr.json")

COLOR_FILE = os.path.join(BASE, "color_change")
SIZE_FILE = os.path.join(BASE, "size_change")

# 数字前缀：如 "08 Weiß" -> ("08", "Weiß")
_NUM_PREFIX = re.compile(r"^(\d+)\s*(.*)$")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_reverse(mapping):
    """映射是 原始(英) -> 目标语言；反查得到 目标语言 -> 原始(英)。

    多对一时（如 'Azurblau' 同时来自 Azure / Cerulean）取第一次出现的原始值；
    当前数据里 'Azurblau' 并未出现，若将来出现且需要区分，可在此处扩展。
    """
    rev = {}
    for orig, target in mapping.items():
        rev.setdefault(target, orig)
    return rev


def convert_value(value, rev, fr_map):
    """德文值 -> 原始英文 -> 法文；规则见模块 docstring 第 3 条。"""
    orig = rev.get(value)
    if orig is not None and fr_map.get(orig) is not None:
        return fr_map[orig]
    m = _NUM_PREFIX.match(value)
    if m and m.group(2):
        rest = convert_value(m.group(2), rev, fr_map)
        if rest != m.group(2):
            return f"{m.group(1)} {rest}"
    return value  # 数字/全大写等无映射值，保持原样


def convert_file(path, rev, fr_map):
    """读入文件（保留空行与 CRLF 行尾），逐行转换后直接覆盖写回。

    返回 (转换行数, 未转换行数, {未转换值: 次数})。
    """
    with open(path, "rb") as f:
        parts = f.read().split(b"\r\n")

    out = []
    converted = 0
    kept = 0
    kept_counter = {}
    for part in parts:
        line = part.decode("utf-8")
        s = line.strip()
        if not s:
            out.append(line)  # 空行原样保留
            continue
        new = convert_value(s, rev, fr_map)
        if new != s:
            converted += 1
            out.append(new)
        else:
            kept += 1
            kept_counter[s] = kept_counter.get(s, 0) + 1
            out.append(s)

    with open(path, "wb") as f:
        f.write("\r\n".join(out).encode("utf-8"))
    return converted, kept, kept_counter


def main():
    # Windows 控制台默认 GBK，先切成 UTF-8 以便正常输出中文/法文
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    color_de = load_json(COLOR_DE)
    color_fr = load_json(COLOR_FR)
    size_de = load_json(SIZE_DE)
    size_fr = load_json(SIZE_FR)

    color_rev = build_reverse(color_de)
    size_rev = build_reverse(size_de)

    print("转换：德 -> 原始数据 -> 法，产出直接覆盖原文件\n")

    for path, rev, fr_map, label in (
        (COLOR_FILE, color_rev, color_fr, "color_change(颜色)"),
        (SIZE_FILE, size_rev, size_fr, "size_change(尺寸)"),
    ):
        converted, kept, kept_counter = convert_file(path, rev, fr_map)
        print(f"[{label}] 共处理 {converted + kept} 行非空：转换 {converted} 行，保持原样 {kept} 行")
        if kept_counter:
            print("  保持原样的值（数字/全大写等）:")
            for v, n in sorted(kept_counter.items()):
                print(f"    {n:4d} x {v!r}")
    print("\n完成。")


if __name__ == "__main__":
    main()
