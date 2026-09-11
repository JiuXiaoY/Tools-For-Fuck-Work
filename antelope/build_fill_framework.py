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
  - mode_customise     : 空占位 {} —— 手动指定某列的填充模式(如 {"Q": "cycle"}，键 = 列字母)，
                         填写后 fill_from_plan.py 会优先使用该模式、跳过自动判断
  - data 中的目标列    : 「col_scope 中 A 未映射、completed 也无可选值」的列由
                         column_defaults.json 配置「指定值 / 多行值文件」，按整列连续
                         循环预展开进 data（按组旋转切片 → sequential 等价），
                         fill_from_plan.py 无需改动；未配置则保留占位 dataTemp
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

from common import (
    ValueFileError,
    column_letter,
    find_residual_placeholders,
    load_ai_columns,
    load_column_defaults,
    load_data_cols,
    load_groups,
    load_json,
    make_sequence,
    parse_column_key,
    resolve_column_values,
    seq_seed,
    setup_log,
    uncovered_cols,
    value_cycle_cols,
    zcfg,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 过程 json（模板分析、列差异）在 intermediate 子目录下；最终 plan 输出到 fill_plan
INTERMEDIATE_DIR = zcfg.INTERMEDIATE_DIR
FILL_PLAN_DIR = zcfg.FILL_PLAN_DIR

# 未覆盖列兜底占位值（与 build_m_data.py 一致）
PLACEHOLDER = "dataTemp"

DEFAULT_DIFF = zcfg.CFG_INTERMEDIATE["column_diff_json"]
DEFAULT_COMPLETED = zcfg.CFG_INTERMEDIATE["completed_json"]
DEFAULT_BLANK = zcfg.CFG_INTERMEDIATE["blank_json"]
DEFAULT_GROUPS = zcfg.CFG_INTERMEDIATE["groups_json"]
DEFAULT_DATA = zcfg.CFG_INTERMEDIATE["data_json"]
DEFAULT_M_DATA = zcfg.DATA_SOURCE_M       # M：自定义数据来源（JSON），补充 A 未映射列
DEFAULT_TEMPLATE_OUTPUT = zcfg.TEMPLATE_OUTPUT   # 产出模板（fill_from_plan 复制其副本填充）
DEFAULT_MODE_CUSTOMISE = zcfg.MODE_CUSTOMISE_FILE   # 共享单文件，按 ACTIVE_CATEGORY 标签分段读取
DEFAULT_COLUMN_DEFAULTS = zcfg.COLUMN_DEFAULTS_FILE  # 目标列（A 未覆盖且无可选值）取值配置
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

    共享单文件结构（默认 intermediate_tpl/mode_customise.json）——**键 = 列字母**
    （Excel 列名，大小写不敏感；兼容直接写列号），与 column_defaults.json 写法统一：
        {
          "_comment":     ["…说明，_ 开头的键忽略…"],
          "yass_fr_coat": {"Q": "cycle", "AT": "sequential"},
          "addr_fr_tops": {"E": "children_only"}
        }
    值只能是 sequential / children_only / cycle 之一。
    只读 raw[ACTIVE_CATEGORY] 分段；兼容旧版扁平结构（无标签分段时整体作为当前类别使用）。
    归一化为 {列号(str): 模式}（内部与 plan/fill_from_plan 一致用列号），
    无法识别的键、非法模式 → 打印警告并忽略。
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

        result = {}
        for key, val in raw.items():
            if str(key).startswith("_"):
                continue                       # 说明键
            mode = str(val)
            col = parse_column_key(key)
            if col is None:
                print(f"⚠️ mode_customise 忽略无法识别的键 {key!r}（请写列字母如 \"AT\"，或列号如 \"46\"）")
                continue
            if mode not in _VALID_MODES:
                print(f"⚠️ mode_customise 忽略列 {column_letter(col)}({col}) 的非法模式 {mode!r}"
                      f"（只能是 {'/'.join(sorted(_VALID_MODES))}）")
                continue
            result[str(col)] = mode
        return result
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


def _sorted_groups(groups):
    """把 groups（{组名: "start & end"}）解析为按起始行排序的 [(组名, start, end, n), ...]。

    非法 spec（不是 "a & b"）跳过。
    """
    parsed = []
    for gname, spec in (groups or {}).items():
        s = str(spec).strip()
        if s.count("&") != 1:
            continue
        try:
            start, end = map(int, [x.strip() for x in s.split("&")])
        except ValueError:
            continue
        if end < start:
            continue
        parsed.append((str(gname), start, end, end - start + 1))
    parsed.sort(key=lambda t: t[1])
    return parsed


def _short(text, limit=28):
    """日志里显示值的前缀（过长截断）。"""
    s = str(text)
    return s if len(s) <= limit else s[: limit] + "…"


def _header(headers, col):
    """列号 → 表头（仅用于日志；取不到返回空串）。"""
    return str((headers or {}).get(int(col)) or "")


def apply_column_defaults(data, groups, col_scope, target_cols, defaults, values_dir,
                          headers=None, a_cols=None, mode_customise=None,
                          placeholder=PLACEHOLDER):
    """目标列（A 未覆盖 且 无可选值）→ 指定值/多行文件的**整列连续循环**填充。

    语义（按需求）：不考虑分组，从数据区第一行起连续循环整列所有数据行：
        第 k 行取值 values[(k-1) % m]      （m = 该列循环序列长度，跨组不重置）
    实现：利用「切片长度恰等于组行数 → fill_from_plan 判定 m==n → sequential」这一点，
    把循环序列**按组旋转切片**写进 plan.data；fill_from_plan.py 无需改动。

    配置来源 intermediate_tpl/column_defaults.json 当前类别分段：
        {"S": {"value": "Coat-001"}, "AT": {"file": "keywords.txt"}, "AN": "…"}
    file 优先，文件缺失/为空退回 value；两者都不行 → 该列保留占位（警告）。
    指定值若以数字结尾 → **序列填充**（"S-0001" → S-0001, S-0002, … 整列连续递增，
    宽度按种子补零）；不想要序列就写 "sequence": false；写 true 则值必须以数字结尾，否则报错。
    值文件出现空行 → 报错退出（约定值文件不允许空值）。

    返回 (report, stats)：report 为逐列明细；stats 为计数汇总。
    """
    report = []
    stats = {"target": len(target_cols), "configured": 0, "unconfigured": 0,
             "skipped": 0, "rows": 0}
    rows = _sorted_groups(groups)
    if not rows:
        print("⚠️ groups 为空，目标列取值配置无法应用")
        return report, stats

    first_start = rows[0][1]
    gaps = [(rows[i][0], rows[i][2], rows[i + 1][0], rows[i + 1][1])
            for i in range(len(rows) - 1) if rows[i][2] + 1 != rows[i + 1][1]]
    total_rows = rows[-1][2] - first_start + 1
    if gaps:
        print(f"⚠️ 组区间不连续（{len(gaps)} 处，如 {gaps[0]}）：目标列仍按「组顺序连续计数」循环"
              f"（与产出行的对应关系可能不连续），请确认分组是否正确")

    target_set = {int(c) for c in target_cols}
    scope_set = {int(c) for c in (col_scope or [])}
    a_set = {int(x) for x in (a_cols or [])}
    # 配置了但不在目标集合的列：跳过并说明原因（绝不覆盖 A 取数/AI 选值的真实数据）
    extra = [int(c) for c in defaults if int(c) not in target_set]
    for col in sorted(extra):
        if col not in scope_set:
            reason = "不在 col_scope（待填列范围）内"
        elif col in a_set:
            reason = "有 A 映射取数"
        else:
            reason = "有可选值（由 ⑦ AI 负责）"
        print(f"⚠️ 配置中的列 {column_letter(col)}({col}) 不在目标集合：{reason} → 跳过，不覆盖真实数据")
        stats["skipped"] += 1

    for col in sorted(target_set):
        tag = f"{column_letter(col)}({col})"          # 日志与配置统一用列字母，如 AN(40)
        entry = defaults.get(str(col))
        if entry is None:
            stats["unconfigured"] += 1
            print(f"⚠️ 列{tag} ({_header(headers, col)}) 未配置 → 保留占位 {placeholder}"
                  f"（{total_rows} 格将写入产出）")
            continue

        try:
            values, source, path = resolve_column_values(entry, values_dir)
        except ValueFileError as exc:
            print("")
            print("=" * 60)
            print(f"❌ {exc}")
            print("=" * 60)
            sys.exit(2)

        if not values:
            stats["unconfigured"] += 1
            print(f"⚠️ 列{tag} ({_header(headers, col)}) 配置了但没有可用值"
                  f"（value/file 都为空或无法解析）→ 保留占位 {placeholder}")
            continue

        forced = (mode_customise or {}).get(str(col))
        if forced == "children_only":
            stats["skipped"] += 1
            print(f"⚠️ 列{tag} ({_header(headers, col)}) 被 mode_customise 指定为 children_only"
                  f"（会跳过每组首行、与整列循环错位）→ 跳过并保留占位；请二选一")
            continue

        # ── 指定值的「序列填充」判断（S-0001 → S-0001, S-0002, … 整列连续递增）──
        seq_flag = (entry or {}).get("sequence")           # None=自动 / True=强制 / False=同值
        seq_values = None
        if source == "value":
            seed = values[0]
            if seq_flag is True and seq_seed(seed) is None:
                print("")
                print("=" * 60)
                print(f"❌ 列{tag} 配置 sequence: true，但指定值 {seed!r} 不以数字结尾，无法递增。")
                print("💡 改成如 \"S-0001\" / \"0001\"，或把 sequence 设为 false （整列同值）。")
                print("=" * 60)
                sys.exit(2)
            use_seq = bool(seq_flag) if seq_flag is not None else (seq_seed(seed) is not None)
            if use_seq:
                seq_values = make_sequence(seed, total_rows)
        elif seq_flag is not None:
            print(f"⚠️ 列{tag} 配置了 sequence，但该列用的是值文件 → 按文件行循环，sequence 不生效")

        m = len(values)
        if seq_values is not None:
            # 序列模式：整列连续递增值（行 k → 种子 + (k-1)），按组切片即可
            for gname, start, end, n in rows:
                pos = start - first_start
                data.setdefault(gname, {})[str(col)] = seq_values[pos:pos + n]
            first_v, last_v = seq_values[0], seq_values[-1]
        else:
            for gname, start, end, n in rows:
                pos = start - first_start                 # 该组首行在整列中的全局位置
                data.setdefault(gname, {})[str(col)] = [values[(pos + i) % m] for i in range(n)]
            first_v, last_v = values[0], values[(total_rows - 1) % m]

        stats["configured"] += 1
        stats["rows"] += total_rows
        report.append({
            "column": col, "column_letter": column_letter(col),
            "header": _header(headers, col), "source": source,
            "file": path, "cycle_len": m, "sequence": seq_values is not None,
            "rows": total_rows, "first": first_v, "last": last_v,
        })
        if seq_values is not None:
            src_desc = f"指定值(序列) {first_v!r}→{last_v!r}"
        elif source == "value":
            src_desc = f"指定值 {values[0]!r}"
        else:
            src_desc = f"文件 {path}（{m} 行）"
        print(f"✅ 列{tag} ({_header(headers, col)}) ← {src_desc} 填 {total_rows} 行 "
              f"[首={_short(first_v)} 末={_short(last_v)}]")

    print(f"📌 目标列 {stats['target']} 个：已配置 {stats['configured']} / 未配置 {stats['unconfigured']}"
          f" / 跳过 {stats['skipped']}（数据 {total_rows} 行、{len(rows)} 组"
          f"{'，组区间连续' if not gaps else '，组区间不连续'}）")
    return report, stats


def assert_no_placeholder_for_choice_columns(data, groups, ai_cols, placeholder=PLACEHOLDER):
    """守门：有可选值(choices)的「A 未覆盖列」不允许残留占位。

    与 ai_pick_attributes.py（⑦）的硬校验是同一条不变量：这些列的值**只能**由 AI 选值提供。
    只要还有「组×列」是占位（AI 没跑 / 只跑了一半 / ⑥ 在 ⑦ 之后重跑把 M 里的 AI 结果覆盖回
    占位 / 回答值不在可选值内被拒），就打印明细并 exit 2，**且不写 plan**，
    避免占位值流进产出 Excel。
    """
    if not ai_cols:
        return
    cols = [c for c, _, _ in ai_cols]
    bad = find_residual_placeholders(data, groups, cols, placeholder)
    if not bad:
        print(f"✅ 有可选值列校验通过（{len(cols)} 列无占位残留）: {cols}")
        return

    total = sum(e["count"] for e in bad.values())
    print("")
    print("=" * 60)
    print(f"❌ 有可选值列仍残留占位：{len(bad)} 列 / 共 {total} 个「组×列」——不写 plan，流程中止。")
    print("=" * 60)
    for col in sorted(bad):
        entry = bad[col]
        header = next((h for c, h, _ in ai_cols if c == col), "")
        idx_show = entry["indexes"][:20]
        more = "..." if len(entry["indexes"]) > 20 else ""
        print(f"   列{column_letter(col)}({col}) ({header}): {entry['count']} 组仍占位   组序号 {idx_show}{more}")
    print("")
    print("💡 先跑 ⑦ 让 AI 把这些列选满：python ai_pick_attributes.py")
    print("   （若 ⑦ 之后又跑过 ⑥ build_m_data.py，M JSON 里的 AI 结果会被占位覆盖 → 需再跑一次 ⑦）")
    sys.exit(2)


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
                        help="列填充模式共享配置文件（键 = 列字母，按 ACTIVE_CATEGORY 标签分段；"
                             "默认 intermediate_tpl/mode_customise.json）")
    parser.add_argument("--column-defaults", default=DEFAULT_COLUMN_DEFAULTS,
                        help="目标列（A 未覆盖且无可选值）取值配置（按 ACTIVE_CATEGORY 标签分段；"
                             "默认 intermediate_tpl/column_defaults.json）")
    parser.add_argument("--columns-report", default=None,
                        help="目标列取值明细 JSON 输出路径（可选，用于审计）")
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

    # ── mode_customise：人工维护的 列 → 强制填充模式（提前读，供目标列冲突检测用）──
    mode_customise = load_mode_customise(args.mode_customise)

    # ── 目标列（A 未覆盖 且 无可选值）：指定值 / 多行值文件 → 整列连续循环 ──
    target_cols = value_cycle_cols(args.diff, args.data, args.completed)
    a_cols = load_data_cols(args.data)
    headers = {c["col"]: c.get("header") for c in (completed.get("columns") or []) if "col" in c}
    column_defaults = load_column_defaults(args.column_defaults)
    if target_cols:
        print(f"🎯 目标列（A 未覆盖 且 无可选值）{len(target_cols)} 个: {target_cols}"
              f"（配置 {args.column_defaults}）")
        report, _stats = apply_column_defaults(
            data, groups, col_scope, target_cols, column_defaults,
            zcfg.COLUMN_VALUES_DIR, headers=headers, a_cols=a_cols,
            mode_customise=mode_customise,
        )
        if args.columns_report:
            os.makedirs(os.path.dirname(os.path.abspath(args.columns_report)) or ".", exist_ok=True)
            with open(args.columns_report, "w", encoding="utf-8") as f:
                json.dump({"columns": report, "stats": _stats,
                           "values_dir": zcfg.COLUMN_VALUES_DIR}, f, ensure_ascii=False, indent=2)
            print(f"📄 目标列取值明细: {args.columns_report}")
    else:
        print("ℹ️ 无目标列（A 未覆盖列全部有可选值），跳过取值配置")

    # ── 守门：有可选值的未覆盖列必须已由 AI 填出真实值（不允许残留占位）──
    ai_cols = load_ai_columns(args.completed, uncovered_cols(args.diff, args.data))
    assert_no_placeholder_for_choice_columns(data, groups, ai_cols)

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
