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
# 国家_类别，如 "fr_dress"；中间产物与 plan 命名以此为基础
ACTIVE_CATEGORY = "fr_tops"

# ⚠️ 中间文件写入目录名（如 "fr_dress"）：即 intermediate/ 下的子目录名
#    目录存在则直接写入，不存在则自动新建（各脚本写入时均自动 mkdir）
#    默认跟随 ACTIVE_CATEGORY，也可单独指定（如 "fr_dress" / "de_coat" …）
INTERMEDIATE_DIR_NAME = ACTIVE_CATEGORY

# ─────────────────────────── 国家配置 ───────────────────────────
# 国家代码：fr / de（Amazon 站），按 ACTIVE_CATEGORY 的国家前缀自动推导
# （"de_dress" -> "de"）；决定模板中「字段枚举表」与「主模板」的工作表名
COUNTRY = ACTIVE_CATEGORY.split("_", 1)[0]

# 各国家模板的工作表名：
#   valid —— 字段枚举表（第1列分组标题、第2列字段名、第3列起可选值）
#   model —— 主模板（row1 的 settings=... 定义 labelRow / attributeRow / dataRow）
SHEET_NAMES = {
    "fr": {"valid": "Valeurs valides", "model": "Modèle"},
    "de": {"valid": "Gültige Werte", "model": "Vorlage"},
}

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

# 当前类别中间产物目录：intermediate/<INTERMEDIATE_DIR_NAME>（不存在时由写入脚本自动创建）
CATEGORY_INTERMEDIATE_DIR = os.path.join(INTERMEDIATE_DIR, INTERMEDIATE_DIR_NAME)


# ─────────────────────── 辅助：按类别取文件名 ───────────────────────
def _cat(name):
    """返回 {国家}_{类别}_{用途} 文件名，如 _cat('blank') -> fr_shirt_blank.json"""
    return f"{ACTIVE_CATEGORY}_{name}.json"


# ─────────────────────── 数据源文件（按 11409 需求统一角色命名）───────────────────────
# ⚠️⚠️⚠️ 每次批次文件名不一致，以下 5 个路径需按本批次实际文件手动修改 ⚠️⚠️⚠️
#   A —— .xlsx 数据文件：提供「分组锚点(第1列有色单元格) + 部分待填列数据(经 col_mapping 取数)」
DATA_SOURCE_A = os.path.join(XLSM_DIR, "8.31v1_fr.xlsx")                # ← 本批次 A（角色名 .xlsx_dataSource）
#   B —— .xlsm 基础模板：已填部分数据列（analysisXlsm 分析 → blank.json，即「已填列」）
TEMPLATE_B = os.path.join(XLSM_DIR, "base.xlsm")                     # ← 本批次 B（角色名 .xlsm_template_base）
#   C —— .xlsm 完整模板：完整列即产出参照（analysisXlsm 分析 → completed.json，即「完整列」）
TEMPLATE_C = os.path.join(XLSM_DIR, "complete.xlsm")                 # ← 本批次 C（角色名 .xlsm_template_complete）
#   产出模板：fill_from_plan 复制此文件作副本并填充（填完自动删多余数据行）
TEMPLATE_OUTPUT = os.path.join(XLSM_DIR, "coat_template_Adam.xlsm")  # ← 本批次产出模板
#   M —— 自定义数据来源(JSON)：补充 A 映射未覆盖到的待填列数据
#        由 build_m_data.py 生成到 中间产物目录 intermediate/<INTERMEDIATE_DIR_NAME>/ 下
DATA_SOURCE_M = os.path.join(CATEGORY_INTERMEDIATE_DIR, ".xlsx_dataSource_m.json")  # M（JSON 格式）

# 旧名兼容别名（新脚本请使用上面的角色名）
DEFAULT_SOURCE_XLSM = DATA_SOURCE_A
DEFAULT_TEMPLATE_XLSM = TEMPLATE_B

# ─────────────────── intermediate/<类别> 过程 json ───────────────────
CFG_INTERMEDIATE = {
    "completed_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("completed")),
    "blank_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("blank")),
    "column_diff_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("column_diff")),
    "groups_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("groups")),
    "data_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("data")),
    "col_mapping_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("col_mapping")),
    # 人工维护：目标列 → 强制填充模式（如 {"17": "cycle"}），⑤ 生成 plan 时读入 mode_customise
    "mode_customise_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("mode_customise")),
    # ai_pick_attributes.py：AI 选值的提示词/结果文件目录
    "ai_prompt_dir": os.path.join(CATEGORY_INTERMEDIATE_DIR, "ai_prompt"),
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
    # analysisXlsm.py：参与解析的工作表（随国家配置变化：fr=Modèle/Valeurs valides，de=Vorlage/Gültige Werte）
    "default_sheets": list(SHEET_NAMES[COUNTRY].values()),
    # 最终填充产出（fill_from_plan 写出；run_all 默认输出）：outputs/{ACTIVE_CATEGORY}_filled.xlsm
    "plan_output_file": os.path.join(OUTPUTS_DIR, f"{ACTIVE_CATEGORY}_filled.xlsm"),
    "default_report_file": None,
    "strict_scope": False,
}
