# -*- coding: utf-8 -*-
"""
extract_sku —— 从抓取的卖家后台文本（如 nineTools/SKU3）中抽取「SKU」标识下的值。

输入文本中每个商品块形如：
    ASIN
    B0H8DJC78J
    SKU
    FJYyas07Sh10aU26YG2961      ← 只保留这一行
    状况
    新品

处理规则：
  1. 只保留紧跟在「SKU」标记后的下一行**非空**字符串；
  2. 其余所有内容（ASIN、状况、菜单文本等）全部删除；
  3. 输出为每行一个字符串，空行删除；
  4. 对结果去重（保留首次出现顺序）。

用法:
    python extract_sku.py                 # 默认处理 nineTools/SKU3，输出 nineTools/SKU3_sku.txt
    python extract_sku.py <输入文件> [-o 输出文件]
"""

import argparse
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.join(BASE, "SKU3")
DEFAULT_OUTPUT = os.path.join(BASE, "SKU3_sku.txt")


def extract_skus(text):
    """提取 SKU 标记后的值并去重。

    返回 (标记总数, 去重后的 SKU 列表[按首次出现顺序])。
    """
    lines = text.splitlines()
    result = []
    seen = set()
    total = 0
    i = 0
    n = len(lines)
    while i < n:
        if lines[i].strip() == "SKU":
            total += 1
            i += 1
            while i < n and not lines[i].strip():  # 跳过空行，取下一非空行
                i += 1
            if i < n:
                v = lines[i].strip()
                if v not in seen:
                    seen.add(v)
                    result.append(v)
        i += 1
    return total, result


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="从抓取文本中抽取「SKU」标记后的值，输出每行一个、去重"
    )
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT,
                        help=f"输入文本路径（默认 {DEFAULT_INPUT}）")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help=f"输出文件路径（默认 {DEFAULT_OUTPUT}）")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ 找不到输入文件: {args.input}")
        sys.exit(1)

    text = open(args.input, encoding="utf-8-sig").read()
    total, skus = extract_skus(text)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write("\n".join(skus) + "\n")

    print(f"✅ 提取完成：SKU 标记 {total} 个 → 去重后 {len(skus)} 个")
    print(f"📄 已写入: {args.output}")


if __name__ == "__main__":
    main()
