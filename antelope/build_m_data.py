# -*- coding: utf-8 -*-
"""
build_m_data —— 生成 M 数据源 JSON（补充 A 映射未覆盖的待填列数据）。

按 MISSING.md 的解决方案（流程待定，先跑通）：
  - 当前为**占位实现**：所缺数据统一用 "dataTemp" 替代，按顺序填充模式
    （每列 = 组行数 个 "dataTemp"），生成与 A 取数同构的 M JSON。
  - 未来替换为真实取数逻辑后，输出格式保持不变，build_fill_framework.py
    的 M 合并（--m-data）即可直接使用，无需改动下游。

输入（默认路径来自 zconfig.constant.py，可传参覆盖）：
  - column_diff.json : 待填列范围 col_scope（C − B）
  - groups.json      : 分组行范围（实际行号，用于计算每组行数 n）
  - data.json        : A 已覆盖的列（M 只补 A 未覆盖的列，A 已有列优先）

输出：
  - xlsm/.xlsx_dataSource_m.json
        { "data": { "<group>": { "<目标列>": ["dataTemp", ...] } } }   （按组形态）

用法:
    python build_m_data.py [-o m.json]
        [--groups groups.json] [--data data.json] [--diff diff.json]
        [--placeholder dataTemp] [--report]
"""

import argparse
import json
import os
import sys

from common import load_col_scope, load_data_cols, load_groups, setup_utf8, zcfg

DEFAULT_OUTPUT = zcfg.DATA_SOURCE_M
DEFAULT_DIFF = zcfg.CFG_INTERMEDIATE["column_diff_json"]
DEFAULT_GROUPS = zcfg.CFG_INTERMEDIATE["groups_json"]
DEFAULT_DATA = zcfg.CFG_INTERMEDIATE["data_json"]


def build_m_data(col_scope, groups, a_cols, placeholder):
    """为 A 未覆盖的待填列生成 M 数据（占位值 placeholder，顺序填充）。"""
    m_data = {}
    for gname, spec in (groups or {}).items():
        spec = str(spec).strip()
        if "&" not in spec:
            continue
        try:
            start_w, end_w = map(int, spec.split("&"))
        except ValueError:
            continue
        n = end_w - start_w + 1
        gdata = {}
        for col in col_scope:
            if str(col) not in a_cols:          # 只补 A 未覆盖的列
                gdata[str(col)] = [placeholder] * n
        if gdata:
            m_data[str(gname)] = gdata
    return m_data


def main():
    parser = argparse.ArgumentParser(
        description="生成 M 数据源 JSON（占位实现：所缺数据统一 dataTemp，顺序填充）"
    )
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help="M JSON 输出路径（默认 xlsm/.xlsx_dataSource_m.json）")
    parser.add_argument("--diff", default=DEFAULT_DIFF,
                        help="column_diff JSON 路径（取 col_scope）")
    parser.add_argument("--groups", default=DEFAULT_GROUPS,
                        help="groups JSON 路径（取分组行范围）")
    parser.add_argument("--data", default=DEFAULT_DATA,
                        help="A 取数 data JSON 路径（A 已覆盖的列不重复生成）")
    parser.add_argument("--placeholder", default="dataTemp",
                        help="占位值（默认 dataTemp）")
    parser.add_argument("--report", action="store_true",
                        help="打印每个组的补充列清单")
    args = parser.parse_args()

    setup_utf8()

    col_scope = load_col_scope(args.diff)
    groups = load_groups(args.groups)
    a_cols = load_data_cols(args.data)

    if not col_scope:
        print("⚠️ col_scope 为空（column_diff.json 缺失或 no only_in_completed）")
        sys.exit(1)
    if not groups:
        print("⚠️ groups 为空，无法计算组行数")
        sys.exit(2)

    m_data = build_m_data(col_scope, groups, a_cols, args.placeholder)
    result = {"data": m_data, "placeholder": args.placeholder}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    total = sum(len(v) for v in m_data.values())
    print(f"col_scope 共 {len(col_scope)} 列；A 已覆盖 {len(a_cols)} 列；M 补充 {total} 个「组×列」（占位 {args.placeholder}）")
    if args.report:
        for gname, cols in m_data.items():
            print(f"  {gname}: {sorted(cols, key=int)}")
    print(f"结果已写入: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
