# -*- coding: utf-8 -*-
"""
读取 column_diff.py 生成的差异 JSON 中的 only_in_completed 内容，
生成「基础填充框架」——即一个符合 fill_from_plan.py 约定的 plan 骨架。

骨架中会自动填好：
  - description        : 生成说明
  - source_file        : 数据源（来自 completed 分析 JSON 的 source_file）
  - template_file      : 待填充模板（来自 blank 分析 JSON 的 source_file）
  - output_file        : 输出占位（默认 outputs/shirt_fr_filled.xlsm）
  - data_start_row     : 数据起始行（模板标准 settings.dataRow，来自 column_diff.json）
  - col_scope          : only_in_completed 的全部列号
  - mode_customise     : 空占位 {} —— 手动指定某列的填充模式(如 {"1": "cycle"})，
                         填写后 fill_from_plan.py 会优先使用该模式、跳过自动判断
  - groups             : 来自 groups 来源 JSON（默认 intermediate/groups_from_excel.json），
                         该 JSON 由 build_groups_from_excel.py 的「流水线产出」生成，
                         包含相对行号的分组行范围
  - data               : 来自 data 来源 JSON（默认 intermediate/data_from_excel.json），
                         由 build_data_from_excel.py 生成（每组每列具体值的序列）；
                         缺失时回退为每组每列的 [] 空占位

不含示例内容（无 choices / samples / 示例值）。
groups 来自分组来源 JSON；data 来自 data 来源 JSON（缺失则 [] 占位），再交给 fill_from_plan.py。

用法:
    python build_fill_framework.py [diff.json] [-o output.json]
        [--completed completed.json] [--blank blank.json]
        [--groups groups.json] [--data data.json] [--output-file xxx]
默认:
    diff      = intermediate/shirt_fr_column_diff.json
    completed = intermediate/shirt_fr_completed.json
    blank     = intermediate/shirt_fr_blank.json
    groups    = intermediate/groups_from_excel.json（若存在）
    data      = intermediate/data_from_excel.json（若存在，否则 [] 占位）
    output    = fill_plan/shirt_fr_fill_framework.json
"""
import argparse
import importlib.util
import json
import os
import sys

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

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 过程 json（模板分析、列差异）在 intermediate 子目录下；最终 plan 输出到 fill_plan
INTERMEDIATE_DIR = zcfg.INTERMEDIATE_DIR
FILL_PLAN_DIR = zcfg.FILL_PLAN_DIR

DEFAULT_DIFF = zcfg.CFG_INTERMEDIATE["column_diff_json"]
DEFAULT_COMPLETED = zcfg.CFG_INTERMEDIATE["completed_json"]
DEFAULT_BLANK = zcfg.CFG_INTERMEDIATE["blank_json"]
DEFAULT_GROUPS = zcfg.CFG_INTERMEDIATE["groups_json"]
DEFAULT_DATA = zcfg.CFG_INTERMEDIATE["data_json"]
DEFAULT_OUTPUT = zcfg.CFG_FILL_PLAN["framework_json"]
DEFAULT_PLAN_OUTPUT_FILE = os.path.join(zcfg.OUTPUTS_DIR, "shirt_fr_filled.xlsm")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_groups(path):
    """读取分组来源 JSON 的 groups 字段；文件不存在时返回空 dict。"""
    if not path or not os.path.exists(path):
        return {}
    try:
        data = load_json(path)
    except Exception:
        return {}
    return data.get("groups") or {}


def load_data(path, col_scope, groups):
    """读取 data 来源 JSON 的 data 字段；缺失时回退为每组每列的 [] 空占位。

    返回形状: { group: { str(col): [值...] } }
    """
    if path and os.path.exists(path):
        try:
            data = load_json(path).get("data") or {}
        except Exception:
            data = {}
        if data:
            return data
    return {gname: {str(col): [] for col in col_scope} for gname in (groups or {})}


def build_plan(diff, completed, blank, plan_output_file, groups=None, data=None):
    """生成基础填充框架（plan 骨架）。

    groups: 分组行范围 dict（相对行号），来自 groups 来源 JSON；缺省为空 {}。
    data:   每组每列具体数据 {group: {col_str: [...]}}；缺省为空 {}。
    """
    only_in_completed = diff.get("by_col", {}).get("only_in_completed", [])
    col_scope = sorted(c["col"] for c in only_in_completed if "col" in c)

    # 数据起始行：以 column_diff.json 的模板标准 settings.dataRow 为唯一真源，
    # 缺省回退 7（fill_from_plan 默认）
    diff_settings = diff.get("settings") or {}
    data_start_row = diff_settings.get("dataRow") or 7

    return {
        "description": (
            "基础填充框架：由 column_diff.py 的 only_in_completed 生成，"
            "col_scope 已就绪；groups 行范围来自 groups 来源 JSON，"
            "data 来源占位或用 data 来源 JSON 填充，再交给 fill_from_plan.py。"
        ),
        "source_file": completed.get("source_file"),
        "template_file": blank.get("source_file"),
        "output_file": plan_output_file,
        "data_start_row": data_start_row,
        "col_scope": col_scope,
        "mode_customise": {},
        "groups": groups if groups is not None else {},
        "cycle_threshold": None,
        "data": data if data is not None else {},
    }


def main():
    parser = argparse.ArgumentParser(description="由列差异生成基础填充框架（plan 骨架）")
    parser.add_argument("diff", nargs="?", default=DEFAULT_DIFF,
                        help="column_diff.py 输出的差异 JSON 路径")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help="输出 JSON 文件路径")
    parser.add_argument("--completed", default=DEFAULT_COMPLETED,
                        help="completed 分析 JSON 路径（取 source_file 作为数据源文件）")
    parser.add_argument("--blank", default=DEFAULT_BLANK,
                        help="blank 分析 JSON 路径（取 source_file 作为模板）")
    parser.add_argument("--groups", default=DEFAULT_GROUPS,
                        help="分组来源 JSON 路径（取 groups 字段作为分组行范围）；不存在则留空")
    parser.add_argument("--data", default=DEFAULT_DATA,
                        help="data 来源 JSON 路径（取 data 字段作为每组每列数据）；不存在则按 col_scope 填 [] 占位")
    parser.add_argument("--output-file", default=DEFAULT_PLAN_OUTPUT_FILE,
                        help="plan 中的 output_file 字段（占位）")
    args = parser.parse_args()

    diff = load_json(args.diff)
    completed = load_json(args.completed)
    blank = load_json(args.blank)
    groups = load_groups(args.groups)
    only_in_completed = diff.get("by_col", {}).get("only_in_completed", [])
    col_scope = sorted(c["col"] for c in only_in_completed if "col" in c)
    data = load_data(args.data, col_scope, groups)

    plan = build_plan(diff, completed, blank, args.output_file,
                      groups=groups, data=data)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"col_scope 共 {len(plan['col_scope'])} 列: {plan['col_scope']}")
    print(f"groups 共 {len(plan['groups'])} 组: {plan['groups']}（来源 {args.groups}）")
    print(f"data 已填充（来源 {args.data}，未提供则 col_scope 列填 [] 占位）")
    print(f"结果已写入: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
