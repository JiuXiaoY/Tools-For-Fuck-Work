# -*- coding: utf-8 -*-
"""
parent_actions —— ⑨ 填充产出后，对「父体行」（每组起始行）执行的额外动作。

父体行 = plan.groups 里每组的起始行（数据源 A 中 A 列有背景填充色的锚点行），
实际 Excel 行 = 起始行 + (data_start_row − 1)；它不会被 ⑨ 的「多余行删除」波及，
所以在本模块里直接按实际行号操作即可。

目前支持两种动作，全部由 intermediate_tpl/parent_actions.json 按 ACTIVE_CATEGORY
分段配置；**不配置 = 完全不动**（产物与不接本 hook 时逐格一致）：

  1. row_fill     整行加**静态背景色**：真正的单元格填充（openpyxl PatternFill solid），
                  不是「选中/阅读模式」那种点一下才有、点走就消失的高亮效果。
                  columns 为空 → 铺满整行（到模板最后一列，当前 323 列 LK）。
  2. clear_values 清除该行**指定列的值**（只清 value，不动字体/底色等格式）。

调用点：fill_from_plan.py 在「填充循环 + 多余行删除」之后、wb.save() 之前调用一次——
因此只多一次函数调用，不会对 .xlsm 做第二次加载/保存（避免 round-trip 丢图片/图表）。

配置示例（键 = 列字母，与 column_defaults.json / mode_customise.json 同一套写法）：
    {
      "_comment": ["…"],
      "yass_fr_coat": {
        "row_fill":     { "color": "FFF2CC", "columns": null },
        "clear_values": { "columns": ["S", "T"] }
      }
    }
"""

import os
import re

from openpyxl.styles import PatternFill

from common import load_json, parse_column_key, zcfg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG = zcfg.PARENT_ACTIONS_FILE

_HEX_RE = re.compile(r"^[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$")


def normalize_color(color):
    """颜色 → openpyxl 可用的 8 位 ARGB（如 "FFF2CC" → "FFFFF2CC"）；空值 → None。

    非法写法抛 ValueError（由调用方报错退出，避免静默涂错色）。
    """
    if color is None:
        return None
    s = str(color).strip().lstrip("#").upper()
    if not s:
        return None
    if not _HEX_RE.match(s):
        raise ValueError(f"颜色写法非法 {color!r}（应为 6 位或 8 位十六进制，如 \"FFF2CC\" 或 \"FFFFF2CC\"）")
    return s if len(s) == 8 else "FF" + s


def parse_column_spec(spec, max_column, what="columns"):
    """列范围说明 → 列号列表 [int...]。

    - None / "" / "all" / "*" → 1..max_column（整行）
    - 区间："A:AW" 或 "A-AW"
    - 列表："A,B,AN" 或 ["A", "B", "AN"]（字母或列号混合均可，大小写不敏感）
    无法识别的写法抛 ValueError。
    """
    if spec is None or (isinstance(spec, str) and spec.strip().lower() in ("", "all", "*")):
        return list(range(1, max_column + 1))

    if isinstance(spec, (list, tuple)):
        items = [str(x) for x in spec]
    else:
        s = str(spec).strip()
        for sep in (":", "-"):
            if sep in s:
                a, b = s.split(sep, 1)
                ca, cb = parse_column_key(a), parse_column_key(b)
                if ca is None or cb is None:
                    raise ValueError(f"{what} 区间无法识别: {spec!r}（应为 \"A:AW\" 这种写法）")
                lo, hi = sorted((ca, cb))
                return list(range(lo, hi + 1))
        items = [x for x in re.split(r"[,\s]+", s) if x]

    cols = []
    for it in items:
        c = parse_column_key(it)
        if c is None:
            raise ValueError(f"{what} 无法识别的列: {it!r}（应写列字母如 \"AT\"，或列号如 \"46\"）")
        cols.append(c)
    return sorted(set(cols))


def load_parent_actions(path=DEFAULT_CONFIG):
    """读取父体行动作配置，只取当前 ACTIVE_CATEGORY 标签下的部分。

    返回 {"row_fill": {"color": str|None(已归一化), "columns": 原始列范围写法},
          "clear_values": {"columns": 原始列范围写法}}；
    无配置/文件缺失/无当前标签分段 → {"row_fill": {"color": None}, "clear_values": {"columns": []}}
    （即不动作）。语法错误在 apply_parent_actions 里报错（这里只做结构归一化）。
    """
    empty = {"row_fill": {"color": None, "columns": None}, "clear_values": {"columns": []}}
    if not path or not os.path.exists(path):
        return empty
    try:
        raw = load_json(path)
    except Exception:
        return empty
    if not isinstance(raw, dict):
        return empty
    section = raw.get(zcfg.ACTIVE_CATEGORY)
    if not isinstance(section, dict):
        return empty                      # 只有 _comment 或没有当前类别 → 不动作

    rf = section.get("row_fill") if isinstance(section.get("row_fill"), dict) else {}
    cv = section.get("clear_values") if isinstance(section.get("clear_values"), dict) else {}
    return {
        "row_fill": {"color": rf.get("color"), "columns": rf.get("columns")},
        "clear_values": {"columns": cv.get("columns") or []},
    }


def apply_parent_actions(ws, parent_rows, actions, log=print):
    """对父体行执行配置的动作（整行静态底色 / 清除指定列的值）。

    ws          : openpyxl 工作表（产出副本）
    parent_rows : 父体行**实际行号**列表（⑨ 里由各组起始行 + 偏移得到）
    actions     : load_parent_actions() 的结果
    返回报告 dict（写入 ⑨ 的 --report，便于审计）。
    颜色/列写法非法 → 抛 ValueError（调用方报错退出，不写产出）。
    """
    report = {
        "parent_rows": list(parent_rows),
        "row_count": len(parent_rows),
        "fill": None,
        "clear": None,
    }
    if not parent_rows:
        log("ℹ️ 父体行动作：没有父体行，跳过")
        return report

    max_col = ws.max_column or 1
    fill_cfg = (actions or {}).get("row_fill") or {}
    clear_cfg = (actions or {}).get("clear_values") or {}

    color = normalize_color(fill_cfg.get("color"))
    fill_cols = parse_column_spec(fill_cfg.get("columns"), max_col, "row_fill.columns") if color else []
    clear_cols = parse_column_spec(clear_cfg.get("columns"), max_col, "clear_values.columns") \
        if clear_cfg.get("columns") else []

    if not color and not clear_cols:
        log("ℹ️ 父体行动作：未配置（parent_actions.json 当前类别分段为空），跳过")
        return report

    # ① 清除指定列的值（只动 value，不动格式）
    if clear_cols:
        cleared = 0
        touched = 0
        for r in parent_rows:
            for c in clear_cols:
                cell = ws.cell(row=r, column=c)
                if cell.value is not None:
                    cell.value = None
                    cleared += 1
                touched += 1
        report["clear"] = {"columns": clear_cols, "cells": touched, "cleared_with_value": cleared}
        log(f"🧹 父体行清值：{len(parent_rows)} 行 × {len(clear_cols)} 列（{touched} 格，"
            f"其中原本有值的 {cleared} 格已清空）")

    # ② 整行静态底色（真正的单元格填充）
    if color:
        fill = PatternFill(start_color=color, end_color=color, fill_type="solid")
        for r in parent_rows:
            for c in fill_cols:
                ws.cell(row=r, column=c).fill = fill
        report["fill"] = {"color": color, "columns": len(fill_cols),
                          "cells": len(parent_rows) * len(fill_cols),
                          "span": f"{fill_cols[0]}..{fill_cols[-1]}"}
        log(f"🎨 父体行底色（静态填充）：{len(parent_rows)} 行 × {len(fill_cols)} 列"
            f"（{len(parent_rows) * len(fill_cols)} 格，色值 {color}）")

    return report
