# -*- coding: utf-8 -*-
"""
run_all —— antelope 全流程一键运行（模板层缓存 + 数据层重跑 + 注释续跑）。

设计说明：
  - 中间产物分两层（见 zconfig.constant.py）：
      · 模板层（只需跑一次）：blank / completed / column_diff → intermediate_tpl/<类别>/
        只依赖 base.xlsm / complete.xlsm。**三件套（限定词/国家/类型/模板文件）未变
        则 ①②③ 自动跳过**（比较产物与模板文件修改时间）；换模板文件后自动重算。
      · 数据层（每次数据批次重跑）：groups / data / M / ai_prompt → intermediate/<类别>/
        数据文件一换，④~⑨ 全部重跑。
  - 步骤解耦：各步骤只读写各自的 json；某步失败后，把「已完成」的前面步骤行**注释掉**
    再点运行，会从剩余第一行连续跑到结束（不支持跳步，一定是连续后缀）；
  - 不需要 AI 选值（⑥⑦）时注释对应行即可；填充报告默认不生成（见 REPORT_FILE）。

步骤：
    ① 模板解析 B（基础模板）       → intermediate_tpl/<类别>/<类别>_blank.json（模板层，自动跳过）
    ② 模板解析 C（完整模板）       → intermediate_tpl/<类别>/<类别>_completed.json（模板层，自动跳过）
    ③ 列差异（C − B = 待填列）     → intermediate_tpl/<类别>/<类别>_column_diff.json（模板层，自动跳过）
    ④ 分组（数据源 A 有色锚点）    → intermediate/<类别>/<类别>_groups.json（数据层）
    ⑤ A 取数（col_mapping）       → intermediate/<类别>/<类别>_data.json（数据层）
    ⑥ M 占位生成（dataTemp）      → intermediate/<类别>/.xlsx_dataSource_m.json（数据层）
    ⑦ AI 网页选值（有可选值列）    → 更新 M（数据层，弹浏览器）
    ⑧ 生成 plan                  → fill_plan/<类别>_fill_framework.json
    ⑨ 填充模板副本（fill_from_plan）→ outputs/<类别>_filled.xlsm（取配置）

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
    print("")
    print(label)
    print("-" * 40)
    result = subprocess.run(cmd, cwd=BASE)
    if result.returncode != 0:
        print(f"❌ {label} 失败（exit {result.returncode}），流程中止。")
        print("💡 修复后：把上面【已完成】的步骤行注释掉，再点运行，"
              "会从本步继续连续跑到结束（前面产物已保留，不会重复）。")
        sys.exit(1)
    print(f"✅ {label} OK")


def _is_fresh(out: str, *inputs: str) -> bool:
    """产物 out 已存在且比所有输入文件都新 → 无需重跑（模板层只跑一次的判活）。"""
    if not out or not os.path.exists(out):
        return False
    t_out = os.path.getmtime(out)
    return all(os.path.exists(p) and os.path.getmtime(p) <= t_out for p in inputs)


def run_template_step(label: str, cmd: list[str], out: str, inputs) -> None:
    """模板层步骤：产物已是最新则跳过（复用缓存），否则执行。

    强制重跑：删除对应产物 json（或注释本行 + 手动删除）。
    """
    if _is_fresh(out, *inputs):
        print(f"✅ {label} 跳过：{os.path.basename(out)} 已是最新（模板未变，复用缓存）")
        return
    run_step(label, cmd)


def main() -> None:
    # 日志统一写入 log/{当天日期}_atl_{用户}.log（run_all 与各子步骤追加同一文件）
    setup_log()

    py = sys.executable

    print("=" * 60)
    print(f"antelope 全流程（模板层 ①②③ 自动跳过 + 数据层 ④~⑨ 重跑）  类别: {zcfg.ACTIVE_CATEGORY}")
    print("=" * 60)

    # ══════════════════════════════════════════════════════════════════
    # 每行一步。某步失败后：注释掉“已完成”的前面步骤行，再点运行即可从剩余第一行连续跑完。
    # ①②③ 为模板层：产物比模板文件新则自动跳过（无需注释）；④~⑨ 每次数据批次都要重跑。
    # ══════════════════════════════════════════════════════════════════

    # ① 模板解析 B（模板层 → intermediate_tpl/<类别>/<类别>_blank.json）
    run_template_step("① 模板解析 B → blank.json",
                      [py, "analysisXlsm.py", zcfg.TEMPLATE_B, "-o", _CFG["blank_json"]],
                      _CFG["blank_json"], [zcfg.TEMPLATE_B])

    # ② 模板解析 C（模板层 → <类别>_completed.json）
    run_template_step("② 模板解析 C → completed.json",
                      [py, "analysisXlsm.py", zcfg.TEMPLATE_C, "-o", _CFG["completed_json"]],
                      _CFG["completed_json"], [zcfg.TEMPLATE_C])

    # ③ 列差异（模板层 → <类别>_column_diff.json，依赖 ①②）
    run_template_step("③ 列差异（C − B）→ column_diff.json",
                      [py, "column_diff.py"],
                      _CFG["column_diff_json"], [_CFG["blank_json"], _CFG["completed_json"]])

    # ④ 分组（数据层 → intermediate/<类别>/<类别>_groups.json）
    run_step("④ 分组（数据源 A 锚点）→ groups.json", [py, "build_groups_from_excel.py"])   # 数据层，每次重跑

    # ⑤ A 取数（数据层 → data.json）
    run_step("⑤ A 取数（col_mapping）→ data.json", [py, "build_data_from_excel.py"])       # 数据层，每次重跑

    # ⑥ M 占位生成（数据层 → .xlsx_dataSource_m.json）
    run_step("⑥ M 占位生成 → .xlsx_dataSource_m.json", [py, "build_m_data.py"])            # 数据层，每次重跑

    # ⑦ AI 网页选值（数据层；有可选值列；弹浏览器，更新 M）
    run_step("⑦ AI 网页选值（有可选值列，弹浏览器）", [py, "ai_pick_attributes.py"])       # 不需要可注释本行

    # ⑧ 生成 plan（→ fill_plan/<类别>_fill_framework.json）
    run_step("⑧ 生成 plan → " + zcfg.CFG_FILL_PLAN["framework_json"],
             [py, "build_fill_framework.py"])                                              # 已完成可注释本行

    # ⑨ 填充模板副本（→ outputs/<类别>_filled.xlsm）
    fill_cmd = [py, "fill_from_plan.py", zcfg.CFG_FILL_PLAN["default_plan_json"],
                "-o", zcfg.CFG_RUN["plan_output_file"]]
    if REPORT_FILE:
        fill_cmd += ["--report", REPORT_FILE]
    run_step("⑨ 填充模板副本 → " + zcfg.CFG_RUN["plan_output_file"], fill_cmd)            # 已完成可注释本行

    print("")
    print("=" * 60)
    print("✅ 全流程完成")
    print(f"   输出: {zcfg.CFG_RUN['plan_output_file']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
