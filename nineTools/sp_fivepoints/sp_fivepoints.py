# -*- coding: utf-8 -*-
"""
sp_fivepoints —— 把德法双语五点描述 Markdown 转成「纯内容」xlsx。

输入（默认 y_addr&yass/de_feasibility_domain/coat/coat_bullet_points_de_fr.md）结构：
    ## 产品 001
    **原始商品：** ......
    | 要点 | 德语 | 德语字符数 | 法语 | 法语字符数 |
    |---:|---|---:|---|---:|
    | 1 | Design & Stil: ... | 230 | Style et Design: ... | 234 |
    ...（每个产品固定 5 行）

输出 xlsx 布局（无表头、无任何其他内容）：
    第 1 行   = 第 1 个产品的德语 1~5 点（第 1~5 列）
    第 2 行   = 第 2 个产品的德语 1~5 点
    ...
    第 N 行   = 第 N 个产品的德语 1~5 点
    第 N+1 行、第 N+2 行 = 空两行
    第 N+3 行 = 第 1 个产品的法语 1~5 点
    ...
    即：德语整块 → 空两行 → 法语整块，除此之外不写任何单元格。

用法:
    python sp_fivepoints.py                       # 默认输入，输出到本目录 coat_bullet_points_de_fr.xlsx
    python sp_fivepoints.py <输入md> [-o 输出xlsx]
"""

import argparse
import io
import os
import re
import sys

from openpyxl import Workbook

BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.abspath(
    os.path.join(
        BASE, "..", "..", "y_addr&yass", "de_feasibility_domain", "coat",
        "coat_bullet_points_de_fr.md",
    )
)

PRODUCT_RE = re.compile(r"^##\s*产品\s*(\S+)\s*$")
ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|")


def parse_markdown(path):
    """解析 Markdown，返回 [(产品号, [德语1..5], [法语1..5]), ...]。"""
    with io.open(path, "r", encoding="utf-8") as fh:
        lines = fh.read().splitlines()

    products = []
    cur_no = None
    cur_de = {}
    cur_fr = {}

    def flush():
        if cur_no is None:
            return
        missing = [i for i in range(1, 6) if i not in cur_de or i not in cur_fr]
        if missing:
            raise ValueError("产品 %s 缺少第 %s 点" % (cur_no, missing))
        products.append(
            (cur_no, [cur_de[i] for i in range(1, 6)], [cur_fr[i] for i in range(1, 6)])
        )

    for line in lines:
        head = PRODUCT_RE.match(line.strip())
        if head:
            flush()
            cur_no = head.group(1)
            cur_de, cur_fr = {}, {}
            continue
        if cur_no is None:
            continue  # 跳过标题/说明等表格外文本
        if not ROW_RE.match(line.strip()):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 5:
            raise ValueError(
                "产品 %s 的表格行不是 5 列（要点/德语/德语字符数/法语/法语字符数）: %r"
                % (cur_no, line.strip())
            )
        idx, de, _de_len, fr, _fr_len = cells
        i = int(idx)
        if not 1 <= i <= 5:
            continue  # 表格分隔行等异常行
        if not de or not fr:
            raise ValueError("产品 %s 第 %d 点存在空内容" % (cur_no, i))
        cur_de[i] = de
        cur_fr[i] = fr

    flush()
    if not products:
        raise ValueError("未从 %s 中解析到任何产品" % path)
    return products


def write_xlsx(products, out_path):
    """德语整块 → 空两行 → 法语整块；不写表头、不写其他内容。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "fivepoints"

    n = len(products)
    fr_start = n + 3  # 德语占 1..N，N+1、N+2 空两行，法语从 N+3 开始

    for offset, (_no, de, fr) in enumerate(products):
        for col, text in enumerate(de, start=1):
            ws.cell(row=1 + offset, column=col).value = text
        for col, text in enumerate(fr, start=1):
            ws.cell(row=fr_start + offset, column=col).value = text

    wb.save(out_path)
    return n, fr_start


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(
        description="德法双语五点描述 Markdown -> 纯内容 xlsx（德语块 / 空两行 / 法语块）"
    )
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT, help="输入 Markdown 文件")
    parser.add_argument("-o", "--output", default=None, help="输出 xlsx 路径")
    args = parser.parse_args()

    in_path = os.path.abspath(args.input)
    if not os.path.isfile(in_path):
        print("[ERROR] 输入文件不存在: %s" % in_path)
        return 1

    out_path = args.output or os.path.join(
        BASE, os.path.splitext(os.path.basename(in_path))[0] + ".xlsx"
    )
    out_path = os.path.abspath(out_path)

    products = parse_markdown(in_path)
    n, fr_start = write_xlsx(products, out_path)

    print("输入: %s" % in_path)
    print("输出: %s" % out_path)
    print("产品数: %d" % n)
    print("布局: 德语 第 1~%d 行（每行 5 列）| 第 %d、%d 行空 | 法语 第 %d~%d 行"
          % (n, n + 1, n + 2, fr_start, fr_start + n - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
