# antelope 目录说明

`dealExcel_refactoring/antelope` —— Amazon 模板(.xlsm/.xlsx) 填充流水线的核心脚本与过程数据目录。

## 目录结构

```
antelope/
  zconfig.constant.py     路径与配置项集中声明（唯一真源，所有脚本共享）
  analysisXlsm.py         ① 解析模板：表头 + 字段可选值 -> JSON
  column_diff.py          ② 列差异：对比 completed / blank 的列 -> 列出待填充列
  build_groups_from_excel.py  ③ 分组：按数据源第一列填充色锚点 -> 行范围
  build_data_from_excel.py    ④ 取数：按列映射读数据源 excel -> 每组每列数据
  build_fill_framework.py     ⑤ 生成 plan 骨架：汇总上述过程 json -> plan
  fill_from_plan.py           ⑥ 填充：按 plan 把 data 写入模板副本
  intermediate/           各步骤「过程 json」（模板分析、列差异、分组、取数、列映射）
  fill_plan/              最终填充计划 plan 骨架
  xlsm/                   模板 / 数据源 excel
```

## 流水线流程

```
② completed / blank 模板分析(analysisXlsm.py)
   -> shirt_fr_blank.json / shirt_fr_completed.json
③ 列差异(column_diff.py)
   -> shirt_fr_column_diff.json  （含模板标准 settings，唯一真源）
④ 分组(build_groups_from_excel.py)
   -> groups_from_excel.json
⑤ 取数(build_data_from_excel.py)
   -> data_from_excel.json
⑥ 生成 plan(build_fill_framework.py)
   -> fill_plan/shirt_fr_fill_framework.json
⑦ 填充(fill_from_plan.py)
   -> outputs/*.xlsx
```

## 各脚本说明与运行方式

> 所有脚本的默认路径与配置项统一集中到 `zconfig.constant.py`，
> **直接 `python <脚本>.py` 运行 main 即可，无需额外参数**。

### `analysisXlsm.py` — 解析模板
- 输入：模板 `.xlsm`（默认 `xlsm/shirt_template_Adam.xlsm`，见 `zconfig.DEFAULT_TEMPLATE_XLSM`）
- 输出：`intermediate/shirt_fr_blank.json`（`CFG_INTERMEDIATE["blank_json"]`）
- 解析 `Modèle` 表头与 `Valeurs valides` 可选值。

### `column_diff.py` — 列差异
- 输入：`shirt_fr_completed.json` + `shirt_fr_blank.json`
- 输出：`shirt_fr_column_diff.json`
- 输出 `settings`（模板标准，含 dataRow），是 `data_start_row` 与列范围的**唯一真源**。

### `build_groups_from_excel.py` — 分组
- 输入：数据源 excel（默认 `outputs` 目录最新 `.xlsx`；也可传具体文件）
- 输出：`intermediate/groups_from_excel.json`
- 以数据源第一列有可见填充色的单元格为父体锚点，把相对行号（相对 `data_start_row`）写成组行范围；`data_start_row` 缺省从 `shirt_fr_column_diff.json` 的 `settings.dataRow` 读取。

### `build_data_from_excel.py` — 取数
- 输入：数据源 excel（`--source-excel`，默认 `zconfig.DEFAULT_SOURCE_XLSM`）+ 分组 + 列映射
- 输出：`intermediate/data_from_excel.json`
- 按列映射（`data_col_mapping.json`：源列字母 → 目标列字母，一对多表示同份复制）对每个分组行范围取 **非空值**，写入 `data[group][col]`；`data_start_row` 从 `shirt_fr_column_diff.json` 读取。

### `build_fill_framework.py` — 生成 plan
- 输入：`column_diff` / `completed` / `blank` / `groups` / `data` 过程 json
- 输出：`fill_plan/shirt_fr_fill_framework.json`
- data_start_row 从 `column_diff.json` 的 settings 读取。

### `fill_from_plan.py` — 填充
- 输入：plan(`.json`)，默认 `fill_plan/example_from_givingtree.json`
- 输出：`outputs/*.xlsx`
- 按 plan 把 data 写入模板副本，相对行号通过 `offset = data_start_row - 1` 换算成实际行（**天然支持负相对行号**），并清理多余空行。

## 配置项（`zconfig.constant.py`）

- 顶层目录：`REPO_ROOT`、`ANTELOPE_DIR`、`XLSM_DIR`、`INTERMEDIATE_DIR`、`FILL_PLAN_DIR`、`OUTPUTS_DIR`
- 数据源/模板：`DEFAULT_SOURCE_XLSM`、`DEFAULT_TEMPLATE_XLSM`
- 过程 json：`CFG_INTERMEDIATE`（completed/blank/column_diff/groups/data/col_mapping）
- plan：`CFG_FILL_PLAN`（framework / 默认 plan）
- 运行项：`CFG_RUN`（默认工作表、回退 data_start_row、填充输出、strict_scope）

## 列映射（`intermediate/data_col_mapping.json`）

源 excel 列 → plan 目标列的映射，多来源 `sources` 数组，字母形式，支持一对多（同一份数据复制到多个目标列）：

```json
{ "sources": [ { "name": "excel_01", "mapping": { "K": ["BY","BZ"], ... } } ] }
```
