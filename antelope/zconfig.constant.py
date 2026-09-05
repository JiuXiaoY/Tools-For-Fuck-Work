# -*- coding: utf-8 -*-
"""
zconfig.constant —— antelope 目录下的集中路径与配置项。

所有脚本（analysisXlsm / build_groups_from_excel / build_data_from_excel /
build_fill_framework / column_diff / fill_from_plan）统一从这里 import
默认路径与运行配置，做到「直接 python 运行 main 即可，无需额外传参」。

命名规范：文件/目录名统一为  {限定词}_{国家}_{类型}_{简短用途}
  - 限定词：模板集标识（如 addr / eva …）。**限定词、国家、类型 三段中任一部分
    不同 → 三件套(base/complete/输出模板)就是不同的** → 模板层中间产物需重新生成
  - 国家：fr、de …（Amazon 站）
  - 类型：shirt、coat、dress、pants、tops …
  - 用途：blank / completed / column_diff / groups / data / col_mapping / fill_framework …

中间产物分层：
  - intermediate_tpl/<ACTIVE_CATEGORY>/      模板层（只需跑一次）：blank / completed / column_diff
    + 人工维护固定文件 col_mapping（随模板集固定）
    —— 只依赖 base.xlsm / complete.xlsm；三件套不变则复用，不随数据文件重跑
  - intermediate/<ACTIVE_CATEGORY>/          数据层（每次数据批次都要重跑）：
    groups / data / ai_prompt / .xlsx_dataSource_m.json
    —— 依赖数据源 A，数据文件一换就要重新生成
  - intermediate_tpl/mode_customise.json     列填充模式手动配置（共享单文件，按 ACTIVE_CATEGORY 标签分段）

清理提示：清中间产物时删 intermediate/ 与 intermediate_tpl/ 需谨慎——
col_mapping 是人工维护的固定文件（放 intermediate_tpl/<类别>/ 下），删前先确认有备份或已提交 git。

顶层目录结构：
    antelope/
      xlsm/              模板与数据源 excel
      intermediate_tpl/<category>/   模板层「只需跑一次」的过程 json
      intermediate/<category>/   数据层「每次重跑」的过程 json
      fill_plan/         最终填充计划 plan 骨架（{category}_fill_framework.json）
      outputs/           填充产出（fill_from_plan 写出）
"""
import os

# ─────────────────────────── 当前批次（模板集 + 数据）───────────────────────────
# 三段式 {限定词}_{国家}_{类型}，如 "addr_fr_tops"；中间产物与 plan 命名以此为基础。
# 限定词、国家、类型 任一部分不同 → 三件套(模板)不同 → 模板层需重新生成。
ACTIVE_CATEGORY = "addr_fr_tops"

# 解析三段：限定词 / 国家 / 类型（兼容旧的 {国家}_{类型} 两段写法）
_AC_PARTS = ACTIVE_CATEGORY.split("_")
if len(_AC_PARTS) >= 3:
    QUALIFIER = _AC_PARTS[0]
    COUNTRY = _AC_PARTS[1]
    TYPE = "_".join(_AC_PARTS[2:])
else:  # 兼容旧式 {国家}_{类型}
    QUALIFIER = ""
    COUNTRY = _AC_PARTS[0]
    TYPE = "_".join(_AC_PARTS[1:])

# ⚠️ 中间文件写入目录名（如 "addr_fr_tops"）：intermediate/ 与 intermediate_tpl/ 下的子目录名
#    默认跟随 ACTIVE_CATEGORY，也可单独指定
INTERMEDIATE_DIR_NAME = ACTIVE_CATEGORY

# ─────────────────────────── 国家配置 ───────────────────────────
# 国家代码：fr / de（Amazon 站），来自 ACTIVE_CATEGORY 的第二段（"addr_fr_tops" -> "fr"）；
# 决定模板中「字段枚举表」与「主模板」的工作表名
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
FILL_PLAN_DIR = os.path.join(ANTELOPE_DIR, "fill_plan")
OUTPUTS_DIR = os.path.join(REPO_ROOT, "outputs")

# 模板层目录（只需跑一次）：intermediate_tpl/<ACTIVE_CATEGORY>/ —— blank/completed/column_diff
TEMPLATE_INTERMEDIATE_DIR = os.path.join(ANTELOPE_DIR, "intermediate_tpl")
TEMPLATE_CATEGORY_INTERMEDIATE_DIR = os.path.join(TEMPLATE_INTERMEDIATE_DIR, INTERMEDIATE_DIR_NAME)

# 列填充模式手动配置（共享单文件，按 ACTIVE_CATEGORY 标签分段，如 {"addr_fr_tops": {"17": "cycle"}}）
MODE_CUSTOMISE_FILE = os.path.join(TEMPLATE_INTERMEDIATE_DIR, "mode_customise.json")

# 数据层目录（每次数据批次重跑）：intermediate/<ACTIVE_CATEGORY>/
INTERMEDIATE_DIR = os.path.join(ANTELOPE_DIR, "intermediate")
CATEGORY_INTERMEDIATE_DIR = os.path.join(INTERMEDIATE_DIR, INTERMEDIATE_DIR_NAME)


# ─────────────────────── 辅助：按类别取文件名 ───────────────────────
def _cat(name):
    """返回 {限定词}_{国家}_{类型}_{用途} 文件名，如 _cat('blank') -> addr_fr_tops_blank.json"""
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

# ─────────────────── 中间产物 json（模板层 + 数据层）───────────────────
CFG_INTERMEDIATE = {
    # —— 模板层（只需跑一次，放 intermediate_tpl/<类别>/）——
    #   只依赖 base.xlsm / complete.xlsm，与数据文件无关；
    #   另含人工维护的 col_mapping（源 excel 列 → 目标模板列映射，随模板集固定）
    "completed_json": os.path.join(TEMPLATE_CATEGORY_INTERMEDIATE_DIR, _cat("completed")),
    "blank_json": os.path.join(TEMPLATE_CATEGORY_INTERMEDIATE_DIR, _cat("blank")),
    "column_diff_json": os.path.join(TEMPLATE_CATEGORY_INTERMEDIATE_DIR, _cat("column_diff")),
    "col_mapping_json": os.path.join(TEMPLATE_CATEGORY_INTERMEDIATE_DIR, _cat("col_mapping")),
    # —— 数据层（每次数据批次都要重跑，放 intermediate/<类别>/）——
    "groups_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("groups")),
    "data_json": os.path.join(CATEGORY_INTERMEDIATE_DIR, _cat("data")),
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
