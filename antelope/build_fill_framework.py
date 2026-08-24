# -*- coding: utf-8 -*-
"""
读取 column_diff.py 生成的差异 JSON 中的 only_in_completed 内容，
生成「基础填充框架」——即一个符合 fill_from_plan.py 约定的 plan 骨架。

骨架中会自动填好：
  - description        : 生成说明
  - source_file        : 数据源（来自 completed 分析 JSON 的 source_file）
  - template_file      : 待填充模板（来自 blank 分析 JSON 的 source_file）
  - output_file        : 输出占位（默认 outputs/shirt_fr_filled.xlsm）
  - data_start_row     : 数据起始行（来自 completed 分析 JSON 的 settings.dataRow）
  - col_scope          : only_in_completed 的全部列号
  - mode_customise     : 空占位 {} —— 手动指定某列的填充模式(如 {"1": "cycle"})，
                         填写后 fill_from_plan.py 会优先使用该模式、跳过自动判断
  - cycle_threshold    : null
  - groups / data      : 留空占位 —— 组的行范围与列→组归属暂不确定，
                         由使用者后续手动补充后再交给 fill_from_plan.py

不含任何示例内容（无 choices / samples / 示例值）。
groups / data 均留空，由使用者后续手动补充行范围与数据后再交给 fill_from_plan.py。

用法:
    python build_fill_framework.py [diff.json] [-o output.json]
        [--completed completed.json] [--blank blank.json] [--output-file xxx]
默认:
    diff      = intermediate/shirt_fr_column_diff.json
    completed = intermediate/shirt_fr_completed.json
    blank     = intermediate/shirt_fr_blank.json
    output    = fill_plan/shirt_fr_fill_framework.json
"""
import argparse
import json
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 过程 json（模板分析、列差异）在 intermediate 子目录下；最终 plan 输出到 fill_plan
INTERMEDIATE_DIR = os.path.join(BASE_DIR, "intermediate")
FILL_PLAN_DIR = os.path.join(BASE_DIR, "fill_plan")

DEFAULT_DIFF = os.path.join(INTERMEDIATE_DIR, "shirt_fr_column_diff.json")
DEFAULT_COMPLETED = os.path.join(INTERMEDIATE_DIR, "shirt_fr_completed.json")
DEFAULT_BLANK = os.path.join(INTERMEDIATE_DIR, "shirt_fr_blank.json")
DEFAULT_OUTPUT = os.path.join(FILL_PLAN_DIR, "shirt_fr_fill_framework.json")
DEFAULT_PLAN_OUTPUT_FILE = os.path.join("outputs", "shirt_fr_filled.xlsm")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_plan(diff, completed, blank, plan_output_file):
    """生成基础填充框架（plan 骨架）。"""
    only_in_completed = diff.get("by_col", {}).get("only_in_completed", [])
    col_scope = sorted(c["col"] for c in only_in_completed if "col" in c)

    # 数据起始行：优先 completed 的 settings.dataRow，缺省回退 7（fill_from_plan 默认）
    settings = completed.get("settings") or {}
    data_start_row = settings.get("dataRow") or 7

    return {
        "description": (
            "基础填充框架：由 column_diff.py 的 only_in_completed 生成，"
            "col_scope 已就绪；groups 的行范围与列→组归属暂不确定，需手动补充后再交给 fill_from_plan.py。"
        ),
        "source_file": completed.get("source_file"),
        "template_file": blank.get("source_file"),
        "output_file": plan_output_file,
        "data_start_row": data_start_row,
        "col_scope": col_scope,
        "mode_customise": {},
        "groups": {},
        "cycle_threshold": None,
        "data": {},
    }


def main():
    parser = argparse.ArgumentParser(description="由列差异生成基础填充框架（plan 骨架）")
    parser.add_argument("diff", nargs="?", default=DEFAULT_DIFF,
                        help="column_diff.py 输出的差异 JSON 路径")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help="输出 JSON 文件路径")
    parser.add_argument("--completed", default=DEFAULT_COMPLETED,
                        help="completed 分析 JSON 路径（取 source_file / settings.dataRow）")
    parser.add_argument("--blank", default=DEFAULT_BLANK,
                        help="blank 分析 JSON 路径（取 source_file 作为模板）")
    parser.add_argument("--output-file", default=DEFAULT_PLAN_OUTPUT_FILE,
                        help="plan 中的 output_file 字段（占位）")
    args = parser.parse_args()

    diff = load_json(args.diff)
    completed = load_json(args.completed)
    blank = load_json(args.blank)

    plan = build_plan(diff, completed, blank, args.output_file)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"col_scope 共 {len(plan['col_scope'])} 列: {plan['col_scope']}")
    print(f"groups/data 已留空占位，待补充行范围后交给 fill_from_plan.py")
    print(f"结果已写入: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
