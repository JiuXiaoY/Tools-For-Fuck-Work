# -*- coding: utf-8 -*-
"""
zconfig.constant —— antelope 目录下的集中路径与配置项。

所有脚本（analysisXlsm / build_groups_from_excel / build_data_from_excel /
build_fill_framework / column_diff / fill_from_plan）统一从这里 import
默认路径与运行配置，做到「直接 python 运行 main 即可，无需额外传参」。

命名规范：文件/目录名统一为  {国家}_{类别}_{简短用途}
  - 国家：fr、de …（Amazon 站）
  - 类别：shirt、coat、dress …
  - 用途：blank / completed / column_diff / groups / data / col_mapping / fill_framework …

类别抽象：后续新增其他类别或 xlsm，只需改 CATEGORY，程序无需改动。

顶层目录结构：
    antelope/
      xlsm/              模板与数据源 excel
      intermediate/<category>/   该类别各步骤的「过程 json」
                               （模板分析、列差异、分组、data 来源、列映射）
      fill_plan/         最终填充计划 plan 骨架（{category}_fill_framework.json）
      outputs/           填充产出（fill_from_plan 写出）
"""
import os

# ─────────────────────────── 当前类别 ───────────────────────────
# 国家_类别，如 "fr_shirt"；中间产物与 plan 命名以此为基础
ACTIVE_CATEGORY = "fr_shirt"

# ─────────────────────────── 顶层目录 ───────────────────────────
# 本仓库根目录（dealExcel_refactoring）
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# antelope 目录本身
ANTELOPE_DIR = os.path.dirname(os.path.abspath(__file__))

# 各子目录
XLSM_DIR = os.path.join(ANTELOPE_DIR, "xlsm")
INTERMEDIATE_DIR = os.path.join(ANTELOPE_DIR, "intermediate")
FILL_PLAN_DIR = os.path.join(ANTELOPE_DIR, "fill_plan")
OUTPUTS_DIR = os.path.join(REPO_ROOT, "outputs")

# 当前类别中间产物目录：intermediate/fr_shirt
CATEGORY_INTERMEDIATE_DIR = os.path.join(INTERMEDIATE_DIR, ACTIVE_CATEGORY)


# ─────────────────────── 辅助：按类别取文件名 ───────────────────────
def _cat(name):
    """返回 {国家}_{类别}_{用途} 文件名，如 _cat('blank') -> fr_shirt_blank.json"""
    return f"{ACTIVE_CATEGORY}_{name}.json"


# ─────────────────────── 过程数据源 excel ─────────────────────────
# 数据源(模板分析源 / build_data 取数源) —— 默认指向旧数据源文件
DEFAULT_SOURCE_XLSM = os.path.join(XLSM_DIR, "TheTimeMachine@Partof.xlsm")
# 模板(待填充)文件
DEFAULT_TEMPLATE_XLSM = os.path.join(XLSM_DIR, "shirt_template_Adam.xlsm")

# ─────────────────── intermediate/fr_shirt 过程 json ───────────────────
CFG_INTERMEDIATE = {
    "completed_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("completed")),
    "blank_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("blank")),
    "column_diff_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("column_diff")),
    "groups_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("groups")),
    "data_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("data")),
    "col_mapping_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("col_mapping")),
}

# ─────────────────────── fill_plan 输出 json ───────────────────────
CFG_FILL_PLAN = {
    # 最终填充计划骨架：fill_plan/fr_shirt_fill_framework.json
    "framework_json": os.path.join(FILL_PLAN_DIR, _cat("fill_framework")),
    # 默认填充计划（fill_from_plan 读取）
    "default_plan_json": os.path.join(FILL_PLAN_DIR, _cat("fill_framework")),
}

# ─────────────────────── 可运行配置项 ───────────────────────
CFG_RUN = {
    # build_groups_from_excel.py：分组锚点检测失败时兜底 data_start_row
    "fallback_data_start_row": 7,
    # build_fill_framework.py / build_data_from_excel.py：兜底数据起始行
    "fallback_data_row": 8,
    # analysisXlsm.py：参与解析的工作表
    "default_sheets": ["Valeurs valides", "Modèle"],
    # fill_from_plan.py：默认输出
    "plan_output_file": os.path.join(OUTPUTS_DIR, "result_filled.xlsm"),
    "default_report_file": None,
    "strict_scope": False,
}
