# -*- coding: utf-8 -*-
"""
从「流水线最终产出」的 excel 生成 groups（填充计划所需的行范围）。

约定（与 example_from_givingtree.json 一致）：
  - 读取 excel 第一列（A 列），有可见背景填充色的单元格所在行 = 父体锚点行；
  - 每个锚点行 = 一个组的起始行，组结束行 = 下一个锚点行 - 1；
  - 最后一个组的结束行 = excel 最大行（max_row）；
  - groups 中写入「相对行号」（相对 data_start_row，1-based），
    实际行号 = 相对行号 + data_start_row - 1（与 fill_from_plan.py 的换算一致）。

有色判断逻辑与 services/utils.py 的 cell_has_fill 一致
（排除白色 / 黑色 / 透明等非可见填充）。

用法:
    python build_groups_from_excel.py [excel 路径或目录] [-o output.json]
        [--data-start-row N] [--scan-from N] [--end-row N]
默认:
    input          = outputs（目录则取其中最新的 .xlsx）
    output         = intermediate/groups_from_excel.json（自命名）
    data_start_row = 7
"""
import argparse
import json
import os
import sys
from pathlib import Path

import openpyxl
from openpyxl.cell.cell import Cell

BASE_DIR = Path(__file__).resolve().parent
INTERMEDIATE_DIR = BASE_DIR / "intermediate"

DEFAULT_INPUT_PATH = "outputs"
DEFAULT_OUTPUT_PATH = INTERMEDIATE_DIR / "groups_from_excel.json"
DEFAULT_DATA_START_ROW = 7

# 与 services/utils.py 的 _TRANSPARENT 一致：这些 rgb 视为"无可见填充"
_TRANSPARENT = {"FFFFFF", "000000", "FFFFFFFF", "00000000", "00FFFFFF"}


def cell_has_fill(cell: Cell) -> bool:
    """第一列单元格是否有可见背景填充色（复制自 services/utils.py）。"""
    fill = cell.fill
    if fill is None or fill.fill_type is None:
        return False
    for color in (fill.fgColor, fill.bgColor):
        if color is None:
            continue
        if color.type == "rgb" and color.rgb:
            rgb = color.rgb.upper()
            if len(rgb) == 8:
                rgb = rgb[2:]
            if rgb not in _TRANSPARENT:
                return True
        if color.type == "indexed" and color.indexed not in (None, 0, 64):
            return True
        if color.type == "theme" and color.theme not in (None, 0):
            return True
    return False


def resolve_input(path: str) -> Path:
    """输入可以是具体 .xlsx 文件，也可以是目录（取其中最新的 .xlsx）。"""
    p = Path(path)
    if p.is_dir():
        candidates = sorted(p.glob("*.xlsx"), key=lambda f: f.stat().st_mtime, reverse=True)
        if not candidates:
            raise FileNotFoundError(f"目录 {p} 下没有 .xlsx 文件")
        return candidates[0]
    if not p.exists():
        raise FileNotFoundError(f"找不到 excel 文件: {p}")
    return p


def find_anchor_rows(ws, scan_from: int) -> list[int]:
    """扫描第一列，返回所有有色单元格的行号（升序）。

    注意：必须在 read_only 模式下用 iter_rows 顺序遍历；
    用 ws.cell() 随机访问会导致大文件性能灾难。
    """
    anchors = []
    for row in ws.iter_rows(min_col=1, max_col=1):
        r = row[0].row
        if r < scan_from:
            continue
        if cell_has_fill(row[0]):
            anchors.append(r)
    return anchors


def build_groups(anchors: list[int], end_row: int, data_start_row: int) -> tuple[dict, list[dict]]:
    """由锚点行生成 groups（相对行号）及核对用的 details。"""
    groups = {}
    details = []
    for i, anchor in enumerate(anchors):
        gname = f"group_{i + 1}"
        group_end = (anchors[i + 1] - 1) if i + 1 < len(anchors) else end_row
        if group_end < anchor:
            group_end = anchor
        start_w = anchor - data_start_row + 1
        end_w = group_end - data_start_row + 1
        groups[gname] = f"{start_w} & {end_w}"
        details.append({
            "group": gname,
            "anchor_row": anchor,
            "actual_rows": f"{anchor} & {group_end}",
            "relative_rows": f"{start_w} & {end_w}",
            "row_count": group_end - anchor + 1,
        })
    return groups, details


def main():
    parser = argparse.ArgumentParser(description="从流水线产出 excel 的第一列有色单元格生成 groups")
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT_PATH,
                        help="流水线产出 excel 路径或目录（默认 outputs，取最新 .xlsx）")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT_PATH),
                        help="输出 JSON 文件路径")
    parser.add_argument("--data-start-row", type=int, default=DEFAULT_DATA_START_ROW,
                        help="数据起始行（用于相对行号换算，默认 7）")
    parser.add_argument("--scan-from", type=int, default=1,
                        help="从第几行开始扫描第一列有色单元格（默认 1）")
    parser.add_argument("--end-row", type=int, default=0,
                        help="最后一个组的结束行（默认取 excel 的 max_row）")
    args = parser.parse_args()

    src = resolve_input(args.input)
    wb = openpyxl.load_workbook(src, read_only=True, data_only=True)
    try:
        ws = wb.active
        end_row = args.end_row if args.end_row > 0 else ws.max_row
        anchors = find_anchor_rows(ws, args.scan_from)
        if not anchors:
            print(f"⚠️ 第一列未找到任何有色单元格（{src.name}）")
        groups, details = build_groups(anchors, end_row, args.data_start_row)
    finally:
        wb.close()

    result = {
        "groups": groups,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"共 {len(anchors)} 个有色锚点行 -> {len(groups)} 个组")
    for d in details:
        print(f"  {d['group']}: 锚点行 {d['anchor_row']} -> 实际 {d['actual_rows']} "
              f"(相对 {d['relative_rows']}, {d['row_count']} 行)")
    print(f"结果已写入: {out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
