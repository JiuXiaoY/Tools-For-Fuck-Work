# -*- coding: utf-8 -*-
"""
run_all —— antelope 全流程一键运行（类似 jenkins.py）。

依次执行：
    ① 模板解析 B → blank.json
    ② 模板解析 C → completed.json
    ③ 列差异（C − B）→ column_diff.json
    ④ 分组（数据源 A 有色锚点）→ groups.json
    ⑤ A 取数（col_mapping）→ data.json
    ⑥ M 占位生成（dataTemp）→ .xlsx_dataSource_m.json
    ⑦ AI 网页选值（有可选值的未覆盖列；会弹出浏览器，可 --skip-ai 跳过）
    ⑧ 生成 plan + 填充模板副本 → outputs/fr_dress_filled.xlsm

任一环节失败即中止（退出码非 0）。
所有默认路径来自 zconfig.constant.py（ACTIVE_CATEGORY 决定批次）。

用法:
    python antelope/run_all.py                  # 全流程（含 AI 选值，弹浏览器）
    python antelope/run_all.py --skip-ai        # 跳过 AI 选值（复用现有 M 数据）
    python antelope/run_all.py --output xxx.xlsx   # 指定最终输出文件
"""

import argparse
import os
import subprocess
import sys

from common import zcfg

BASE = os.path.dirname(os.path.abspath(__file__))
_CFG = zcfg.CFG_INTERMEDIATE


def build_steps(skip_ai: bool) -> list[tuple[str, list[str]]]:
    """构造按顺序执行的步骤列表 [(名称, [脚本参数...]), ...]。

    skip_ai=True 时跳过 ⑥ M 占位生成 与 ⑦ AI 选值（M 数据保持现有内容，不覆盖）。
    """
    py = sys.executable
    steps = [
        ("1/8 模板解析 B（基础模板 → blank）",
         [py, "analysisXlsm.py", zcfg.TEMPLATE_B, "-o", _CFG["blank_json"]]),
        ("2/8 模板解析 C（完整模板 → completed）",
         [py, "analysisXlsm.py", zcfg.TEMPLATE_C, "-o", _CFG["completed_json"]]),
        ("3/8 列差异（C − B = 待填列）",
         [py, "column_diff.py"]),
        ("4/8 分组（数据源 A 有色锚点）",
         [py, "build_groups_from_excel.py"]),
        ("5/8 A 取数（col_mapping）",
         [py, "build_data_from_excel.py"]),
    ]
    if not skip_ai:
        steps += [
            ("6/8 M 占位生成（dataTemp）",
             [py, "build_m_data.py"]),
            ("7/8 AI 网页选值（有可选值列，弹浏览器）",
             [py, "ai_pick_attributes.py"]),
        ]
    else:
        steps.append(("6/8 M 占位生成 + 7/8 AI 选值（已跳过，复用现有 M 数据）", None))
    steps.append(("8/8 生成 plan + 填充模板副本",
                  [py, "build_fill_framework.py"]))
    return steps


def main() -> None:
    parser = argparse.ArgumentParser(description="antelope 全流程一键运行")
    parser.add_argument("--skip-ai", action="store_true", help="跳过 AI 网页选值（复用现有 M 数据）")
    parser.add_argument("--output", default=os.path.join(zcfg.OUTPUTS_DIR, "fr_dress_filled.xlsm"),
                        help="最终输出文件路径")
    args = parser.parse_args()

    steps = build_steps(args.skip_ai)

    print("=" * 60)
    print(f"antelope 全流程 — {len(steps)} 步"
          + ("（跳过 AI 选值）" if args.skip_ai else ""))
    print("=" * 60)

    for i, (name, cmd) in enumerate(steps, 1):
        print("")
        print(f"[{i}/{len(steps)}] {name}")
        print("-" * 40)
        if cmd is None:
            print("（跳过）")
            continue
        result = subprocess.run(cmd, cwd=BASE)
        if result.returncode != 0:
            print(f"[{i}/{len(steps)}] {name} 失败（exit {result.returncode}），流程中止。")
            sys.exit(1)
        print(f"[{i}/{len(steps)}] {name} OK")

    # 最后一步：按 plan 填充产出
    print("")
    print(f"[填充] 按 plan 填充模板副本 → {args.output}")
    fill_cmd = [
        sys.executable, "fill_from_plan.py",
        zcfg.CFG_FILL_PLAN["default_plan_json"],
        "-o", args.output,
        "--report", os.path.join(zcfg.OUTPUTS_DIR, "fr_dress_report.json"),
    ]
    result = subprocess.run(fill_cmd, cwd=BASE)
    if result.returncode != 0:
        print("填充失败，流程中止。")
        sys.exit(1)

    print("")
    print("=" * 60)
    print("✅ 全流程完成")
    print(f"   输出: {args.output}")
    print("=" * 60)


if __name__ == "__main__":
    main()
