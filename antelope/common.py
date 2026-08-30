# -*- coding: utf-8 -*-
"""
antelope/common.py —— 各脚本共享的公共工具（配置加载 + JSON/分组/列工具）。

抽取动机：原来 7 个脚本各自重复实现了 zconfig 加载（importlib spec，因为
zconfig.constant.py 文件名含点无法直接 import）与 load_json / load_groups /
load_data_cols / load_col_scope 等小工具。这里统一收敛，行为不变。

用法：
    from common import zcfg, load_json, load_groups, ...
"""

import importlib.util
import json
import os
import sys

# ─────────────────────────────────────────────────────────────────────────── #
# 路径与 sys.path：antelope 与项目根都加入，便于 import zconfig / services
# ─────────────────────────────────────────────────────────────────────────── #
_ANTELOPE_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_ANTELOPE_DIR)
for _p in (_ANTELOPE_DIR, _ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)


# ─────────────────────────────────────────────────────────────────────────── #
# zconfig 加载（zconfig.constant.py 文件名含点，无法用普通 import，故用 spec 加载）
# ─────────────────────────────────────────────────────────────────────────── #
def _load_zconfig():
    _p = os.path.join(_ANTELOPE_DIR, "zconfig.constant.py")
    _spec = importlib.util.spec_from_file_location("zconfig_constant", _p)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)
    return _mod


zcfg = _load_zconfig()   # 模块级单例，所有脚本共享同一份配置


# ─────────────────────────────────────────────────────────────────────────── #
# 通用工具
# ─────────────────────────────────────────────────────────────────────────── #
def setup_utf8():
    """Windows 控制台以 UTF-8 输出（避免 GBK 报错）。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_json(path):
    """读取 JSON；utf-8-sig 兼容带 BOM 的人工编辑文件（如 PowerShell/记事本保存）。"""
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_groups(path):
    """读取 groups JSON 的 groups 字段（分组行范围，实际行号）；缺失/失败返回 {}。"""
    if not path or not os.path.exists(path):
        return {}
    try:
        return load_json(path).get("groups") or {}
    except Exception:
        return {}


def load_data_cols(path):
    """读取 A 取数 data.json 中已覆盖的目标列（去重集合）。"""
    if not path or not os.path.exists(path):
        return set()
    try:
        data = load_json(path).get("data") or {}
    except Exception:
        return set()
    cols = set()
    for col_data in data.values():
        cols.update(str(c) for c in (col_data or {}).keys())
    return cols


def load_col_scope(diff_path):
    """读取 column_diff.json 的 only_in_completed 列号（待填列范围 col_scope）。"""
    if not path_exists(diff_path):
        return []
    try:
        diff = load_json(diff_path)
        only_in_completed = diff.get("by_col", {}).get("only_in_completed", [])
        return sorted(c["col"] for c in only_in_completed if "col" in c)
    except Exception:
        return []


def path_exists(path):
    return bool(path) and os.path.exists(path)


def uncovered_cols(diff_path, data_path):
    """A 未覆盖的待填列：col_scope − A 已覆盖列。"""
    scope = load_col_scope(diff_path)
    a_cols = load_data_cols(data_path)
    return [c for c in scope if str(c) not in a_cols]


def load_ai_columns(completed_path, uncovered):
    """从「A 未覆盖列」中筛出有可选值(choices)的列，返回 [(col, header, choices)]。

    用于 ai_pick_attributes.py（AI 选值）；header 用于生成短标签。
    """
    completed = load_json(completed_path)
    by_col = {c["col"]: c for c in completed.get("columns", [])}
    result = []
    for col in uncovered:
        c = by_col.get(col)
        if not c:
            continue
        choices = c.get("choices") or []
        if choices:
            result.append((col, str(c.get("header", "")), [str(x) for x in choices]))
    return result


# ─────────────────────────────────────────────────────────────────────────── #
# 单元格工具（复用 services/utils.py 的实现，但不触发 services/__init__.py 的
# 包级导入——那样会间接依赖 config.py；utils.py 本身只依赖 openpyxl）
# ─────────────────────────────────────────────────────────────────────────── #
_utils_spec = importlib.util.spec_from_file_location(
    "services_utils", os.path.join(_ROOT, "services", "utils.py")
)
_utils_mod = importlib.util.module_from_spec(_utils_spec)
_utils_spec.loader.exec_module(_utils_mod)
cell_has_fill = _utils_mod.cell_has_fill
