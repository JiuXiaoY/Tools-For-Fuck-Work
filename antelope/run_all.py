# -*- coding: utf-8 -*-
"""
run_all —— antelope 全流程一键运行（模板层缓存 + 数据层重跑 + 注释续跑）。

设计说明：
  - 中间产物分两层（见 zconfig.constant.py）：
      · 模板层：blank / completed / column_diff → intermediate_tpl/<前缀>/<类别>/
        ①② 各自判断：原模板存在就重新解析，否则复用当前类别的分析 JSON。
        ③ 在任一模板重解析、分析 JSON 更新或列差异文件缺失时重新比较。
      · 数据层（每次数据批次重跑）：groups / data / M / ai_prompt → intermediate/<前缀>/<类别>/
        数据文件一换，④~⑨ 全部重跑。
  - 步骤解耦：各步骤只读写各自的 json；某步失败后，把「已完成」的前面步骤行**注释掉**
    再点运行，会从剩余第一行连续跑到结束（不支持跳步，一定是连续后缀）；
  - 不需要 AI 选值（⑥⑦）时注释对应行即可；填充报告默认不生成（见 REPORT_FILE）。

步骤：
    ① 有 B 就解析，否则复用       → intermediate_tpl/<前缀>/<类别>/<类别>_blank.json
    ② 有 C 就解析，否则复用       → intermediate_tpl/<前缀>/<类别>/<类别>_completed.json
    ③ 列差异（C − B = 待填列）     → intermediate_tpl/<前缀>/<类别>/<类别>_column_diff.json（按需重算）
    ④ 分组（数据源 A 有色锚点）    → intermediate/<前缀>/<类别>/<类别>_groups.json（数据层）
    ⑤ A 取数（col_mapping）       → intermediate/<前缀>/<类别>/<类别>_data.json（数据层）
    ⑥ M 占位生成（dataTemp）      → intermediate/<前缀>/<类别>/.xlsx_dataSource_m.json（数据层）
    ⑦ AI 网页选值（有可选值列）    → 更新 M（数据层，弹浏览器）★必须选满，否则 ⑧ 报错中止
    ⑧ 生成 plan                  → fill_plan/<前缀>/<类别>_fill_framework.json
                                    （含目标列取值配置 column_defaults.json 的循环填充）
    ⑨ 填充模板副本（fill_from_plan）→ outputs/<类别>_filled.xlsm（取配置）
                                    （含父体行额外动作：parent_actions.json）

用法：直接运行本文件（python run_all.py），无需任何命令行参数。
"""

import os
import subprocess
import sys

from common import setup_log, zcfg

BASE = os.path.dirname(os.path.abspath(__file__))
_CFG = zcfg.CFG_INTERMEDIATE

# 填充报告 JSON 路径：不需要保持 None；需要时改为如 os.path.join(zcfg.OUTPUTS_DIR, "report.json")
REPORT_FILE = None


def run_step(label: str, cmd: list[str]) -> None:
    """执行一步；失败即中止并提示如何断点续跑。"""
    print(f"\n▶ {label}")
    result = subprocess.run(cmd, cwd=BASE)
    if result.returncode != 0:
        print(f"❌ {label} 失败（exit {result.returncode}），流程中止。")
        print("💡 修复后：把上面【已完成】的步骤行注释掉，再点运行，"
              "会从本步继续连续跑到结束（前面产物已保留，不会重复）。")
        sys.exit(1)
    print(f"✅ {label} OK")


def _column_diff_rebuild_reason(out: str, *inputs: str) -> str | None:
    """列差异文件可复用时返回 None，否则返回需要重算的原因。"""
    if not os.path.isfile(out):
        return "列差异 JSON 不存在"
    t_out = os.path.getmtime(out)
    for path in inputs:
        if not os.path.isfile(path):
            return f"分析 JSON 不存在：{path}"
        if os.path.getmtime(path) > t_out:
            return f"分析 JSON 比列差异更新：{path}"
    return None


def run_template_analysis(label: str, python: str, template: str, out: str) -> bool:
    """有源模板就解析，否则复用分析 JSON。返回本次是否重新解析。"""
    if os.path.isfile(template):
        print(f"ℹ️ {label}：已提供原模板，本次重新解析。\n   原模板：{template}\n   分析 JSON：{out}")
        run_step(label, [python, "analysisXlsm.py", template, "-o", out])
        return True

    if not os.path.isfile(out):
        print(f"❌ {label}：原模板和分析 JSON 均缺失，流程中止。\n   缺少原模板：{template}\n   缺少分析 JSON：{out}")
        sys.exit(1)

    print(f"✅ {label}：未找到原模板，复用当前类别的分析 JSON。\n   原模板：{template}\n   复用 JSON：{out}")
    return False


def main() -> None:
    # 日志按月归档，run_all 与各子步骤在同一天追加到同一文件。
    setup_log()

    py = sys.executable

    print(f"antelope 全流程（有模板就解析，否则复用分析 JSON）  类别: {zcfg.ACTIVE_CATEGORY}")

    # ══════════════════════════════════════════════════════════════════
    # 每行一步。某步失败后：注释掉“已完成”的前面步骤行，再点运行即可从剩余第一行连续跑完。
    # ①②③ 为模板层；④~⑨ 每次数据批次都要重跑。
    # ══════════════════════════════════════════════════════════════════

    blank_path = _CFG["blank_json"]
    completed_path = _CFG["completed_json"]
    diff_path = _CFG["column_diff_json"]
    blank_rebuilt = completed_rebuilt = False

    # ① 模板解析 B（模板层）
    blank_rebuilt = run_template_analysis("① 模板解析 B → blank.json", py, zcfg.TEMPLATE_B, blank_path)

    # ② 模板解析 C（模板层 → <类别>_completed.json）
    completed_rebuilt = run_template_analysis("② 模板解析 C → completed.json", py, zcfg.TEMPLATE_C, completed_path)

    # ③ 列差异（模板层 → <类别>_column_diff.json，依赖 ①②）
    rebuilt_templates = [name for name, rebuilt in (("B", blank_rebuilt), ("C", completed_rebuilt)) if rebuilt]
    if rebuilt_templates:
        reason = f"本次已重新解析模板 {'、'.join(rebuilt_templates)}"
    else:
        reason = _column_diff_rebuild_reason(diff_path, blank_path, completed_path)
    if reason:
        print(f"ℹ️ ③ 列差异：{reason}，重算并写入 {diff_path}")
        run_step("③ 列差异（C − B）→ column_diff.json", [py, "column_diff.py"])
    else:
        print(f"✅ ③ 列差异：分析 JSON 未更新，复用 {diff_path}")

    # ④ 分组（数据层）
    run_step("④ 分组（数据源 A 锚点）→ groups.json", [py, "build_groups_from_excel.py"])   # 数据层，每次重跑

    # ⑤ A 取数（数据层 → data.json）
    run_step("⑤ A 取数（col_mapping）→ data.json", [py, "build_data_from_excel.py"])       # 数据层，每次重跑

    # ⑥ M 占位生成（数据层 → .xlsx_dataSource_m.json）
    run_step("⑥ M 占位生成 → .xlsx_dataSource_m.json", [py, "build_m_data.py"])            # 数据层，每次重跑

    # ⑦ AI 网页选值（数据层；有可选值列；弹浏览器，更新 M）
    #    注意：有可选值的列必须在这里选满，否则 ⑧ 会报错中止（不允许占位流进产出）。
    #    本类别确认「有可选值列」已全部有真实值时，才可注释本行。
    run_step("⑦ AI 网页选值（有可选值列，弹浏览器）", [py, "ai_pick_attributes.py"])       # 不需要可注释本行（见上）

    # ⑧ 生成 plan（→ fill_plan/<前缀>/<类别>_fill_framework.json）
    #    目标列（A 未覆盖且无可选值，如 19/20/40/46）取值见 intermediate_tpl/column_defaults.json：
    #    配置 value 或 values/<国家>_<性别>/ 下的文件，按整列连续填入；未配置则保留 dataTemp 占位。
    run_step("⑧ 生成 plan → " + zcfg.CFG_FILL_PLAN["framework_json"],
             [py, "build_fill_framework.py"])                                              # 已完成可注释本行

    # ⑨ 填充模板副本（→ outputs/<类别>_filled.xlsm）
    #    填充后会对「父体行」（每组起始行）执行额外动作：整行静态底色 / 清指定列的值，
    #    配置见 intermediate_tpl/parent_actions.json（空配置 = 不动作）。
    fill_cmd = [py, "fill_from_plan.py", zcfg.CFG_FILL_PLAN["default_plan_json"],
                "-o", zcfg.CFG_RUN["plan_output_file"]]
    if REPORT_FILE:
        fill_cmd += ["--report", REPORT_FILE]
    run_step("⑨ 填充模板副本 → " + zcfg.CFG_RUN["plan_output_file"], fill_cmd)            # 已完成可注释本行

    print("\n✅ 全流程完成")
    print(f"   输出: {zcfg.CFG_RUN['plan_output_file']}")


if __name__ == "__main__":
    main()
