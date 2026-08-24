# -*- coding: utf-8 -*-
"""
对比两个 fill_plan JSON 文件中的列（columns）差异。

以每列的 "col"（Excel 列号）为唯一标识，输出：
  - only_in_completed : 只存在于 completed 文件的列
  - only_in_blank     : 只存在于 blank 文件的列

同时附上按 "attribute" 标识的差异，便于人工核对。
并把「模板标准 settings」（含 labelRow / attributeRow / dataRow）一并写入输出，
使本文件（fr_shirt_column_diff.json）成为 data_start_row 等模板参数的单一真源。

用法:
    python column_diff.py [completed.json] [blank.json] [-o output.json]
默认:
    completed = fr_shirt_completed.json
    blank     = fr_shirt_blank.json
    output    = fr_shirt_column_diff.json
"""
import argparse
import json
import os
import sys

import importlib.util

# ─────────────────────────────────────────────────────────────────────────── #
# 集中配置加载（zconfig.constant.py 文件名含点，无法用普通 import，故用 spec 加载）
# ─────────────────────────────────────────────────────────────────────────── #
def _load_zconfig():
    _p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "zconfig.constant.py")
    _spec = importlib.util.spec_from_file_location("zconfig_constant", _p)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod


zcfg = _load_zconfig()

# 过程 json（模板分析、列差异）在 intermediate 子目录下
INTERMEDIATE_DIR = zcfg.INTERMEDIATE_DIR

DEFAULT_COMPLETED = zcfg.CFG_INTERMEDIATE["completed_json"]
DEFAULT_BLANK = zcfg.CFG_INTERMEDIATE["blank_json"]
DEFAULT_OUTPUT = zcfg.CFG_INTERMEDIATE["column_diff_json"]


def load_columns(path):
    """读取 JSON 文件，返回 columns 列表。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    columns = data.get("columns")
    if not isinstance(columns, list):
        raise ValueError(f"{path} 中缺少 columns 数组")
    return columns


def load_settings(path):
    """读取 JSON 文件的 settings（模板标准，含 labelRow/attributeRow/dataRow 等）。"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("settings")


def build_index(columns, key_func):
    """按指定 key 建立 {key: column} 映射，key 重复时保留第一个并记录。"""
    index = {}
    duplicates = []
    for col in columns:
        key = key_func(col)
        if key in index:
            duplicates.append(key)
        else:
            index[key] = col
    return index, duplicates


def pick_columns(index, keys):
    """按 keys 从 {key: column} 映射中挑选列，输出精简信息。"""
    rows = []
    for key in sorted(keys, key=lambda k: (k is None, k)):
        col = index[key]
        rows.append({
            "col": col.get("col"),
            "header": col.get("header"),
            "attribute": col.get("attribute"),
            "matched": col.get("matched"),
        })
    return rows


def main():
    parser = argparse.ArgumentParser(description="对比两个 fill_plan JSON 的列差异")
    parser.add_argument("completed", nargs="?", default=DEFAULT_COMPLETED,
                        help="completed 文件路径")
    parser.add_argument("blank", nargs="?", default=DEFAULT_BLANK,
                        help="blank 文件路径")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help="输出 JSON 文件路径")
    args = parser.parse_args()

    completed_cols = load_columns(args.completed)
    blank_cols = load_columns(args.blank)

    # 模板标准 settings（dataRow 等）：以 completed（模板分析）为准，随结果一并写出，
    # 使 fr_shirt_column_diff.json 成为 data_start_row 等模板参数的单一真源
    settings = load_settings(args.completed)

    # 以 col 为唯一标识
    completed_by_col, dup_completed = build_index(completed_cols, lambda c: c.get("col"))
    blank_by_col, dup_blank = build_index(blank_cols, lambda c: c.get("col"))

    cols_only_in_completed = sorted(set(completed_by_col) - set(blank_by_col))
    cols_only_in_blank = sorted(set(blank_by_col) - set(completed_by_col))

    # 以 attribute 为唯一标识（辅助核对）
    completed_by_attr, _ = build_index(completed_cols, lambda c: c.get("attribute"))
    blank_by_attr, _ = build_index(blank_cols, lambda c: c.get("attribute"))
    attrs_only_in_completed = sorted(set(completed_by_attr) - set(blank_by_attr))
    attrs_only_in_blank = sorted(set(blank_by_attr) - set(completed_by_attr))

    result = {
        "settings": settings,
        "compared_files": {
            "completed": args.completed,
            "blank": args.blank,
        },
        "summary": {
            "completed_total": len(completed_cols),
            "blank_total": len(blank_cols),
            "only_in_completed": len(cols_only_in_completed),
            "only_in_blank": len(cols_only_in_blank),
            "duplicate_col_in_completed": dup_completed,
            "duplicate_col_in_blank": dup_blank,
        },
        "by_col": {
            "only_in_completed": pick_columns(completed_by_col, cols_only_in_completed),
            "only_in_blank": pick_columns(blank_by_col, cols_only_in_blank),
        },
        "by_attribute": {
            "only_in_completed": pick_columns(completed_by_attr, attrs_only_in_completed),
            "only_in_blank": pick_columns(blank_by_attr, attrs_only_in_blank),
        },
    }

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"completed: {len(completed_cols)} 列, blank: {len(blank_cols)} 列")
    print(f"仅存在于 completed: {len(cols_only_in_completed)} 列 -> {cols_only_in_completed}")
    print(f"仅存在于 blank:     {len(cols_only_in_blank)} 列 -> {cols_only_in_blank}")
    print(f"结果已写入: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
