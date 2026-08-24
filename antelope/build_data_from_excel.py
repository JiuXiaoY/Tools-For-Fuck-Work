# -*- coding: utf-8 -*-
"""
从「数据源 excel」读取列数据，按列映射填充到 plan 的 data（按分组组织）。

流程与 build_groups_from_excel.py 对称：
  - groups 来源 json（默认 intermediate/fr_shirt/fr_shirt_groups.json）提供分组行范围（相对行号）；
  - 列映射来源 json（默认 intermediate/fr_shirt/fr_shirt_col_mapping.json）提供「源 excel 列 → plan 目标列」映射；
  - 本程序读取数据源 excel：对每个分组、每个源列取「该组范围内该列的非空值」，
    写入目标列；一对多映射（如 K→BY,BZ）表示同一份数据复制到多个目标列；
    映射应用到全部分组；
  - 生成 data 来源 JSON（默认 intermediate/fr_shirt/fr_shirt_data.json）：
        { "data": { <group>: { "<目标列号>": [ 值序列 ] } } }
    交给 build_fill_framework.py 读取后写入 plan 的 data 字段，再交给 fill_from_plan.py。

取数约定（与 fr_shirt_fill_framework.json 一致）：
  - 组实际行范围 = 组相对行 + data_start_row - 1；
  - 每个源列在该组行范围内逐行读，跳过空单元格，只取非空值序列。

用法:
    python build_data_from_excel.py [-o output.json]
        [--groups groups.json] [--col-mapping mapping.json]
        [--source-excel data.xlsx] [--sheet 工作表名] [--diff diff.json]

默认:
    groups       = intermediate/fr_shirt/fr_shirt_groups.json
    col-mapping  = intermediate/fr_shirt/fr_shirt_col_mapping.json
    source-excel = intermediate/../xlsm/TheTimeMachine@Partof.xlsm（占位，不存在则提示）
    diff         = intermediate/fr_shirt/fr_shirt_column_diff.json（取 settings.dataRow 作为 data_start_row，唯一真源）
    output       = intermediate/fr_shirt/fr_shirt_data.json
"""
import argparse
import importlib.util
import json
import os
import sys

import openpyxl
from openpyxl.utils import column_index_from_string, get_column_letter

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
INTERMEDIATE_DIR = zcfg.INTERMEDIATE_DIR

DEFAULT_GROUPS = zcfg.CFG_INTERMEDIATE["groups_json"]
DEFAULT_COL_MAPPING = zcfg.CFG_INTERMEDIATE["col_mapping_json"]
DEFAULT_DIFF = zcfg.CFG_INTERMEDIATE["column_diff_json"]
DEFAULT_SOURCE_EXCEL = zcfg.DEFAULT_SOURCE_XLSM
DEFAULT_OUTPUT = zcfg.CFG_INTERMEDIATE["data_json"]


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_groups(path):
    """读取分组来源 JSON 的 groups 字段；文件不存在或无法解析时返回空 dict。"""
    if not path or not os.path.exists(path):
        return {}
    try:
        return (load_json(path).get("groups") or {})
    except Exception:
        return {}


def load_col_mapping(path):
    """读取列映射来源 JSON 的 sources 数组。

    返回: [ {"name": str, "mapping": {源字母: [target字母,...]}} ]
    """
    if not path or not os.path.exists(path):
        return []
    try:
        return list(load_json(path).get("sources") or [])
    except Exception:
        return []


def parse_col_mapping(sources):
    """字母映射 -> 源列号到目标列号列表的字典。

    返回: { src_col(int): [target_col(int), ...] }
    """
    mapping = {}
    for src in sources:
        for src_letter, target_letters in (src.get("mapping") or {}).items():
            src_col = column_index_from_string(src_letter)
            targets = [column_index_from_string(t) for t in target_letters]
            mapping.setdefault(src_col, [])
            for t in targets:
                if t not in mapping[src_col]:
                    mapping[src_col].append(t)
    return mapping


def data_start_row_from_diff(path, fallback=8):
    """从 column_diff.json 的模板标准 settings.dataRow 取数据起始行；缺失时用 fallback。

    data_start_row 唯一真源为 fr_shirt_column_diff.json（由模板分析得到），不读其他文件。
    """
    try:
        settings = load_json(path).get("settings") or {}
        return int(settings.get("dataRow") or fallback)
    except Exception:
        return fallback


def read_column_values(ws, group_start, group_end, src_col):
    """读某组行范围内某列的非空值序列（跳过空单元格）。"""
    values = []
    for row in range(group_start, group_end + 1):
        cell = ws.cell(row=row, column=src_col)
        v = cell.value
        if v is not None and not (isinstance(v, str) and not v.strip()):
            values.append(v)
    return values


def extract_data(wb, groups, col_mapping, data_start_row, sheet=None):
    """从工作簿按分组 + 列映射提取 data；映射应用于全部组。

    返回: { group: { str(target_col): [值...] } }
    """
    if sheet and sheet in wb.sheetnames:
        ws = wb[sheet]
    else:
        ws_name = "Modèle" if "Modèle" in wb.sheetnames else wb.sheetnames[0]
        ws = wb[ws_name]
    offset = data_start_row - 1

    data = {}
    for gname, spec in (groups or {}).items():
        spec = str(spec).strip()
        if "&" not in spec:
            continue
        try:
            start_w, end_w = map(int, spec.split("&"))
        except ValueError:
            continue
        start_actual = start_w + offset
        end_actual = end_w + offset
        if start_actual < 1 or end_actual < start_actual:
            continue

        gdata = {}
        for src_col, target_cols in col_mapping.items():
            values = read_column_values(ws, start_actual, end_actual, src_col)
            for target in target_cols:
                gdata[str(target)] = list(values)  # 同一份数据复制到多个目标列
        data[gname] = gdata
    return data


def main():
    parser = argparse.ArgumentParser(
        description="从数据源 excel 按分组+列映射生成 data 来源 JSON"
    )
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT,
                        help="输出 data 来源 JSON 路径")
    parser.add_argument("--groups", default=DEFAULT_GROUPS,
                        help="分组来源 JSON 路径（取 groups 字段，相对行号）")
    parser.add_argument("--col-mapping", default=DEFAULT_COL_MAPPING,
                        help="列映射 JSON 路径（取 sources 数组中的字母映射）")
    parser.add_argument("--source-excel", default=DEFAULT_SOURCE_EXCEL,
                        help="数据源 excel 路径（当前为占位，需提供实际文件）")
    parser.add_argument("--sheet", default=None,
                        help="工作表名（默认 'Modèle' 优先，其次第一个工作表）")
    parser.add_argument("--diff", default=DEFAULT_DIFF,
                        help="column_diff JSON 路径（data_start_row 只取 settings.dataRow，唯一真源，不可覆盖）")
    args = parser.parse_args()

    groups = load_groups(args.groups)
    sources = load_col_mapping(args.col_mapping)
    col_mapping = parse_col_mapping(sources)
    # data_start_row 唯一真源：fr_shirt_column_diff.json 的模板标准 settings.dataRow
    data_start_row = data_start_row_from_diff(args.diff, fallback=8)

    if not groups:
        print("⚠️ 分组来源为空或缺失，请先提供分组 json")
        sys.exit(1)
    if not col_mapping:
        print("⚠️ 列映射为空或缺失，请先提供列映射 json")
        sys.exit(2)

    if not os.path.exists(args.source_excel):
        print(f"❌ 找不到数据源 excel: {args.source_excel}")
        print("💡 请通过 --source-excel 指定实际数据源文件路径。")
        sys.exit(3)

    wb = openpyxl.load_workbook(args.source_excel, read_only=True, data_only=True)
    try:
        data = extract_data(wb, groups, col_mapping, data_start_row, sheet=args.sheet)
    finally:
        wb.close()

    result = {"data": data}

    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"数据源: {args.source_excel}（data_start_row={data_start_row}）")
    print(f"groups 共 {len(groups)} 组，列映射源列 {len(col_mapping)} 个")
    for gname in groups:
        cols = data.get(gname, {})
        print(f"  {gname}: {len(cols)} 个目标列")
    print(f"结果已写入: {args.output}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
