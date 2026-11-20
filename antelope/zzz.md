# antelope 模板填充流程

`antelope/` 用于把普通数据源写入 Amazon `.xlsm` 模板副本。源数据和模板按只读方式加载，最终文件写入根目录 `outputs/`。

## 入口

从仓库根目录运行：

```bash
python antelope/run_all.py
```

每个批次开始前，先检查 `zconfig.constant.py` 顶部的手动配置区：

| 配置 | 作用 |
|---|---|
| `ACTIVE_CATEGORY` | 当前类别，格式通常为 `{账号}_{国家}_{类型}` |
| `DATA_SOURCE_A` | 数据源 A，包含分组锚点和部分待填数据 |
| `TEMPLATE_B` | 基础模板 B |
| `TEMPLATE_C` | 完整参照模板 C |
| `TEMPLATE_OUTPUT` | 用于生成最终文件的输出模板 |

当前默认值属于本地批次配置，切换账号、国家、类别或模板时必须重新核对。

## 数据角色

| 角色 | 内容 | 用途 |
|---|---|---|
| A | `.xlsx` 数据源 | 根据 A 列填充色分组，并按 `col_mapping` 读取数据 |
| B | 基础 `.xlsm` 模板 | 分析已有列，生成 `blank.json` |
| C | 完整 `.xlsm` 模板 | 与 B 对比，确定待填列范围 |
| M | `.xlsx_dataSource_m.json` | 补充 A 未覆盖的目标列 |
| D | `outputs/{ACTIVE_CATEGORY}_filled.xlsm` | 最终模板副本 |

基本关系：

```text
C - B = 待填列范围
A + M = 待填数据
TEMPLATE_OUTPUT 的副本 + 待填数据 = D
```

## 九步流程

`run_all.py` 按顺序执行：

| 步骤 | 脚本 | 产物 |
|---:|---|---|
| 1 | `analysisXlsm.py` 分析 B | `intermediate_tpl/<前缀>/<类别>/<类别>_blank.json` |
| 2 | `analysisXlsm.py` 分析 C | `intermediate_tpl/<前缀>/<类别>/<类别>_completed.json` |
| 3 | `column_diff.py` | `<类别>_column_diff.json` |
| 4 | `build_groups_from_excel.py` | `intermediate/<前缀>/<类别>/<类别>_groups.json` |
| 5 | `build_data_from_excel.py` | `intermediate/<前缀>/<类别>/<类别>_data.json` |
| 6 | `build_m_data.py` | `intermediate/<前缀>/<类别>/.xlsx_dataSource_m.json` |
| 7 | `ai_pick_attributes.py` | 更新 M 中具有可选值的列 |
| 8 | `build_fill_framework.py` | `fill_plan/<前缀>/<类别>_fill_framework.json` |
| 9 | `fill_from_plan.py` | `outputs/<类别>_filled.xlsm` |

步骤 1、2 分别检查 B 和 C。放入对应原模板就重新解析。原模板缺席时，复用当前类别对应的分析 JSON。原模板和分析 JSON 都缺时，流程会报错并列出两个路径。

步骤 3 在任意一份原模板重解析后重新计算列差异。两份分析 JSON 都复用时，只在列差异文件缺失或已过期时重算。

运行日志会列出步骤 1、2 的原模板和分析 JSON 路径，说明是重解析、复用还是缺文件中止。步骤 3 会记录重算原因或复用的文件路径。

用同一套模板跑新批次时，保留两份分析 JSON，准备本批数据源 A 和 `TEMPLATE_OUTPUT`，再从原入口启动。需要更新模板分析时，把新的 B 和 C 放到配置指向的位置。

步骤 7 会打开浏览器。只有确认当前类别不需要 AI 选值，或者 M 中所有具有 choices 的列都已有合法值时，才可以注释该步骤。

## 目录与文件性质

前缀取自 `ACTIVE_CATEGORY` 的第一段。例如 `lfda_fr_sweater` 的前缀为 `lfda`，两个中间目录都使用 `lfda/lfda_fr_sweater/`，填充计划放在 `fill_plan/lfda/`。共享的列取值和父体行配置放在 `intermediate_tpl/` 根目录，仍按完整类别名分段。

| 路径 | 性质 | 是否可以整目录清理 |
|---|---|---|
| `xlsm/` | 本地模板和数据源 | 否；目录已被 Git 忽略 |
| `intermediate/<前缀>/<类别>/` | 数据层中间产物 | 换批次后可重新生成，但先确认没有人工结果 |
| `intermediate_tpl/<前缀>/<类别>/` | 模板层分析结果和人工 `col_mapping` | 不可直接整目录删除 |
| `intermediate_tpl/column_defaults.json` | 分类别的目标列取值配置 | 不可随意删除 |
| `intermediate_tpl/parent_actions.json` | 父体行附加动作 | 不可随意删除 |
| `values/<国家>_<性别>/` | 人工维护的多行值文件 | 不可随意删除；格式见 [values/zzz.md](values/zzz.md) |
| `fill_plan/<前缀>/` | 生成的填充计划 | 可以重建，但文件通常较大 |
| `log/YY.MM.log/` | antelope 运行日志，文件名为 `YYYY-MM-DD_atl_<用户>.log` | 可按保留周期清理 |

## 关键配置

### `col_mapping`

位于：

```text
intermediate_tpl/<前缀>/<ACTIVE_CATEGORY>/<ACTIVE_CATEGORY>_col_mapping.json
```

它定义数据源 A 的列如何映射到目标模板列，属于人工维护文件，不应和普通中间产物一起删除。

### `column_defaults.json`

按 `ACTIVE_CATEGORY` 分段，使用 Excel 列字母配置目标列取值：

```json
{
  "addr_de_sweater": {
    "S": {"value": "S-0001", "sequence": true},
    "AQ": {"file": "de_Adam/de_sweater_Adam.txt"}
  }
}
```

- `value`、`file` 和 `sequence` 只给 A 未覆盖且无 choices 的目标列提供默认值。`file` 优先于 `value`。`sequence: true` 让固定值的数字后缀逐行递增。
- 默认值按整列连续填充，跨分组不重置。
- 文件规则和查找顺序见 [values/zzz.md](values/zzz.md)。
- 目标列的 `file` 和 `value` 都没有配置时，该列会保留 `dataTemp` 占位。
- 修改后重新生成填充计划，步骤 9 会读取新计划。

### `parent_actions.json`

步骤 9 保存前，可对每组父体行执行：

- `clear_values`：清指定列的值；
- `set_values`：给指定列写固定值；
- `row_fill`：设置静态背景色。

执行顺序是 `clear_values → set_values → row_fill`。

## 未覆盖列处理规则

未覆盖列只有三种来源：

1. A 通过 `col_mapping` 提供数据。
2. 模板中具有 choices 的列由步骤 7 选择合法值；这些列不允许把占位值带入步骤 8。
3. 没有 choices 的目标列由 `column_defaults.json` 提供固定值，或引用 `values/<国家>_<性别>/` 下的多行值文件。未配置时保留占位。

未覆盖列规则统一维护在本节，不再另建重复的待确认文档。

## 模板写入规则

对每个分组，设该列数据数量为 `m`，组行数为 `n`：

| 条件 | 行为 |
|---|---|
| `m == n` | 保留每项的行位置，空值也占一行 |
| `m == 1` 且 `n > 1` | 把同一个值写入组内每行，例如 AI 每组选择的值 |
| `m == 0` | 跳过 |
| 其他长度 | 告警并跳过 |

父体某列需要留空时，可以在逐行数据中保留父体的空值，或用 `parent_actions.json` 的 `clear_values` 清空该列的父体单元格。

`plan.groups` 保存数据源 A 的实际行号。写入模板时才应用 `data_start_row - 1` 偏移。

## 失败与续跑

- 任一步骤返回非零退出码时，`run_all.py` 立即停止。
- 步骤 4～9 没有自动断点状态；需要续跑时，应确认前置产物有效，再临时注释已经完成的连续前缀步骤。
- 不要为了跳过错误而执行非连续的后缀步骤，步骤之间通过 JSON 文件存在真实依赖。

## 输出检查

流程完成后至少检查：

1. 输出文件名与 `ACTIVE_CATEGORY` 一致。
2. 模板工作表名称符合国家配置。
3. 所有具有 choices 的目标列没有 `dataTemp`。
4. 行数、父子体分组和 `data_start_row` 偏移正确。
5. `.xlsm` 可以由 Excel 正常打开，宏和模板结构仍存在。
