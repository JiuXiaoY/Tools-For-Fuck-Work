# -*- coding: utf-8 -*-
"""
读取 column_diff.py 生成的差异 JSON 中的 only_in_completed 内容，
生成「基础填充框架」——即一个符合 fill_from_plan.py 约定的 plan 骨架。

按 11409 需求的分工（A/B/C/M/D 角色见 zconfig.constant.py）：
  - 待填列范围 col_scope = C(完整模板) − B(基础模板)，来自 column_diff.py；
  - 数据来源 = A(经 col_mapping 取数，build_data_from_excel.py) + M(自定义数据来源 JSON)，
    本脚本把两者合并进 plan 的 data 字段：
      * M JSON 支持两种形态：
          - 按组：{ "data": { "<group>": { "<目标列>": [值...] } } }
          - 全局：{ "<目标列>": [值...] }（应用到全部分组）
      * 合并规则：A 已有的列优先，M 只补「A 未映射到的」列（需求语义）；
      * 值数组允许包含空串 ""（需求：m 包含空数据，空串也算一项，影响模式判断）。

骨架中会自动填好：
  - description        : 生成说明
  - source_file        : 数据源（来自 completed 分析 JSON 的 source_file，即完整模板 C）
  - template_file      : 待填充模板（来自 blank 分析 JSON 的 source_file，即基础模板 B）
  - output_file        : 输出占位（默认 outputs/{ACTIVE_CATEGORY}_filled.xlsm，取配置）
  - data_start_row     : 数据起始行（模板标准 settings.dataRow，来自 column_diff.json；
                         不同模板可能不同；读不到则报错，不做兜底）
  - col_scope          : only_in_completed 的全部列号
  - mode_customise     : 空占位 {} —— 手动指定某列的填充模式(如 {"1": "cycle"})，
                         填写后 fill_from_plan.py 会优先使用该模式、跳过自动判断
  - groups             : 来自 groups 来源 JSON（默认 intermediate/fr_shirt/fr_shirt_groups.json），
                         该 JSON 由 build_groups_from_excel.py 对数据源 A 生成，
                         包含实际行号的分组行范围（无偏移）
  - data               : A 取数(data.json) 与 M 数据合并后的每组每列值序列；
                         两者都缺失时回退为每组每列的 [] 空占位

不含示例内容（无 choices / samples / 示例值）。

用法:
    python build_fill_framework.py [diff.json] [-o output.json]
        [--completed completed.json] [--blank blank.json]
        [--groups groups.json] [--data data.json] [--m-data m.json] [--output-file xxx]
默认:
    diff      = intermediate/fr_shirt/fr_shirt_column_diff.json
    completed = intermediate/fr_shirt_completed.json
    blank     = intermediate/fr_shirt_blank.json
    groups    = intermediate/fr_shirt/fr_shirt_groups.json（若存在）
    data      = intermediate/fr_shirt/fr_shirt_data.json（若存在，否则 [] 占位）
    m-data    = xlsm/.xlsx_dataSource_m.json（若存在；否则不合并）
    output    = fill_plan/fr_shirt_fill_framework.json
"""
import argparse
import json
import os
import sys

from common import load_groups, load_json, setup_log, zcfg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 过程 json（模板分析、列差异）在 intermediate 子目录下；最终 plan 输出到 fill_plan
INTERMEDIATE_DIR = zcfg.INTERMEDIATE_DIR
FILL_PLAN_DIR = zcfg.FILL_PLAN_DIR

DEFAULT_DIFF = zcfg.CFG_INTERMEDIATE["column_diff_json"]
DEFAULT_COMPLETED = zcfg.CFG_INTERMEDIATE["completed_json"]
DEFAULT_BLANK = zcfg.CFG_INTERMEDIATE["blank_json"]
DEFAULT_GROUPS = zcfg.CFG_INTERMEDIATE["groups_json"]
DEFAULT_DATA = zcfg.CFG_INTERMEDIATE["data_json"]
DEFAULT_M_DATA = zcfg.DATA_SOURCE_M       # M：自定义数据来源（JSON），补充 A 未映射列
DEFAULT_TEMPLATE_OUTPUT = zcfg.TEMPLATE_OUTPUT   # 产出模板（fill_from_plan 复制其副本填充）
DEFAULT_MODE_CUSTOMISE = zcfg.MODE_CUSTOMISE_FILE   # 共享单文件，按 ACTIVE_CATEGORY 标签分段读取
DEFAULT_OUTPUT = zcfg.CFG_FILL_PLAN["framework_json"]
DEFAULT_PLAN_OUTPUT_FILE = zcfg.CFG_RUN["plan_output_file"]


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


_VALID_MODES = {"sequential", "children_only", "cycle"}


def load_mode_customise(path):
    """读取人工维护的列填充模式配置，只取当前 ACTIVE_CATEGORY 标签下的部分。

    共享单文件结构（默认 intermediate_tpl/mode_customise.json）：
        {
          "addr_fr_tops": {"17": "cycle", "5": "children_only"},
          "de_pants":     {"1": "sequential"}
        }
    只读取 raw[ACTIVE_CATEGORY] 分段，值为 {列号: "sequential"/"children_only"/"cycle"}；
    兼容旧版扁平结构 {列号: 模式}（无标签分段时整体作为当前类别使用）。
    文件缺失/空/找不到当前标签 → 返回 {}（全部走自动判断）。
    """
    if not path or not os.path.exists(path):
        return {}
    try:
        raw = load_json(path)
        if not isinstance(raw, dict):
            return {}
        section = raw.get(zcfg.ACTIVE_CATEGORY)
        if isinstance(section, dict):
            raw = section                      # 新版：取当前标签分段
        # 否则视为旧版扁平结构，raw 整体使用（其值若是 dict 会被过滤掉）
        return {str(k): str(v) for k, v in raw.items() if str(v) in _VALID_MODES}
    except Exception:
        return {}


def load_m_data(path, groups):
    """读取 M（自定义数据来源 JSON）并归一化为 { group: { str(col): [值...] } }。

    支持两种形态（需求：M 补充 A 未映射到的待填列数据，值数组可含空串 ""）：
      1. 按组：{ "data": { "<group>": { "<目标列>": [值...] } } }
      2. 全局：{ "<目标列>": [值...] }  —— 同一份数据应用到全部分组
    文件缺失或解析失败返回空 dict。
    """
    if not path or not os.path.exists(path):
        return {}
    try:
        raw = load_json(path)
    except Exception:
        return {}

    per_group = raw.get("data")
    if isinstance(per_group, dict):
        # 形态 1：按组
        return {
            str(gname): {str(col): list(vals) for col, vals in (cols or {}).items()}
            for gname, cols in per_group.items()
        }

    # 形态 2：全局（顶层即 列号 → 值数组），应用到所有组
    global_cols = {str(k): list(v) for k, v in raw.items()}
    if not global_cols:
        return {}
    return {
        str(gname): dict(global_cols)
        for gname in (groups or {})
    }


def merge_data(a_data, m_data):
    """合并 A 取数(data.json) 与 M 数据，返回 (合并结果, M 补充的「组×列」数)。

    合并规则（需求语义）：A 已有的列优先，M 只补「A 未映射到的」空缺列；
    M 值数组中的空串 "" 原样保留（参与 fill_from_plan 的 m 计数与模式判断）。
    """
    merged = {}
    added_total = 0
    for gname in set(a_data) | set(m_data):
        a_cols = a_data.get(gname) or {}
        m_cols = m_data.get(gname) or {}
        cols = {str(c): list(v) for c, v in a_cols.items()}
        added = 0
        for col, vals in m_cols.items():
            if str(col) not in cols:
                cols[str(col)] = list(vals)
                added += 1
        merged[str(gname)] = cols
        added_total += added
    return merged, added_total


def fill_uncovered_with_temp(data, groups, col_scope, temp_value="dataTemp"):
    """未覆盖的待填列统一填占位值（按顺序/sequential 写入）。

    对 col_scope 中「每组每列都缺失」的列，填入 [temp_value] * 组行数；
    这样 fill_from_plan 里 m == n → sequential 顺序写入（每个单元格都是占位值）。
    默认占位值 dataTemp（与 build_m_data.py 一致，见 MISSING.md 解决方案）。
    """
    filled = 0
    for gname, spec in (groups or {}).items():
        spec = str(spec).strip()
        if "&" not in spec:
            continue
        try:
            start_w, end_w = map(int, spec.split("&"))
        except ValueError:
            continue
        n = end_w - start_w + 1
        gdata = data.setdefault(str(gname), {})
        for col in col_scope:
            if str(col) not in gdata:
                gdata[str(col)] = [temp_value] * n
                filled += 1
    return filled


def build_plan(diff, completed, blank, plan_output_file, template_output=None,
               mode_customise=None, groups=None, data=None):
    """生成基础填充框架（plan 骨架）。

    template_output: 产出模板（fill_from_plan 复制其副本并填充）；缺省回退 blank.source_file。
    mode_customise:  人工维护的 列 → 强制填充模式（来自 mode_customise 配置文件）。
    groups: 分组行范围 dict（实际行号，来自 build_groups_from_excel.py）；缺省为空 {}。
    data:   每组每列具体数据 {group: {col_str: [...]}}；缺省为空 {}。
    """
    only_in_completed = diff.get("by_col", {}).get("only_in_completed", [])
    col_scope = sorted(c["col"] for c in only_in_completed if "col" in c)

    # 数据起始行：唯一真源 = column_diff.json 的模板标准 settings.dataRow；
    # 不同模板可能不同；读不到说明流程有问题（缺 column_diff 或 settings），直接报错，不做兜底
    diff_settings = diff.get("settings") or {}
    data_row = diff_settings.get("dataRow")
    if data_row is None:
        raise ValueError(
            "column_diff.json 缺少 settings.dataRow（数据起始行）：请先运行 analysisXlsm + column_diff 生成完整的 column_diff.json"
        )
    data_start_row = int(data_row)

    return {
        "description": (
            "基础填充框架：由 column_diff.py 的 only_in_completed 生成，"
            "col_scope 已就绪；groups 行范围来自 groups 来源 JSON，"
            "data 来源占位或用 data 来源 JSON 填充，再交给 fill_from_plan.py。"
        ),
        "source_file": completed.get("source_file"),
        "template_file": template_output or blank.get("source_file"),
        "output_file": plan_output_file,
        "data_start_row": data_start_row,
        "col_scope": col_scope,
        "mode_customise": mode_customise if mode_customise is not None else {},
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
    parser.add_argument("--m-data", default=DEFAULT_M_DATA,
                        help="M 数据来源 JSON 路径（补充 A 未映射列；支持按组/全局两种形态）；不存在则不合并")
    parser.add_argument("--output-file", default=DEFAULT_PLAN_OUTPUT_FILE,
                        help="plan 中的 output_file 字段（占位）")
    parser.add_argument("--template-output", default=DEFAULT_TEMPLATE_OUTPUT,
                        help="产出模板路径（fill_from_plan 复制其副本并填充；默认 zconfig.TEMPLATE_OUTPUT）")
    parser.add_argument("--mode-customise", default=DEFAULT_MODE_CUSTOMISE,
                        help="列填充模式共享配置文件（按 ACTIVE_CATEGORY 标签分段；默认 intermediate_tpl/mode_customise.json）")
    args = parser.parse_args()

    setup_log()

    diff = load_json(args.diff)
    completed = load_json(args.completed)
    blank = load_json(args.blank)
    groups = load_groups(args.groups)
    only_in_completed = diff.get("by_col", {}).get("only_in_completed", [])
    col_scope = sorted(c["col"] for c in only_in_completed if "col" in c)
    data = load_data(args.data, col_scope, groups)

    # ── M 数据合并（需求：剩余未映射列由 M 补充）──
    m_data = load_m_data(args.m_data, groups)
    if m_data:
        data, m_added = merge_data(data, m_data)
        print(f"✅ M 数据合并：{m_added} 个「组×列」由 M 补充（来源 {args.m_data}）")
    else:
        print(f"⚠️ M 数据缺失或为空（{args.m_data}），跳过 M 合并")

    # ── 未覆盖列兜底：统一填占位值 dataTemp（sequential 顺序写入）──
    temp_filled = fill_uncovered_with_temp(data, groups, col_scope)

    # ── mode_customise：人工维护的 列 → 强制填充模式 ──
    mode_customise = load_mode_customise(args.mode_customise)

    plan = build_plan(diff, completed, blank, args.output_file,
                      template_output=args.template_output,
                      mode_customise=mode_customise,
                      groups=groups, data=data)

    # 输出目录不存在则自动新建
    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    print(f"✅ plan 已生成: {args.output}")
    print(f"   col_scope {len(plan['col_scope'])} 列: {plan['col_scope']}")
    print(f"   groups {len(plan['groups'])} 组（来源 {args.groups}）")
    print(f"   template_file: {plan['template_file']}")
    if temp_filled:
        print(f"⚠️ 未覆盖 {temp_filled} 个「组×列」→ 占位 dataTemp")
    if mode_customise:
        print(f"   mode_customise: {mode_customise}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
