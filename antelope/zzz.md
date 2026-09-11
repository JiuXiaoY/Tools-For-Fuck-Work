# antelope 目录说明 — 从数据源到最终产出物的完整流程

> `antelope/` = Amazon 模板(.xlsm/.xlsx) 填充流水线：解析模板 → 找差异列 → 分组 → 取数 → 生成填充计划(plan) → 按 plan 把数据写入模板副本。
> 全程**模板只读**，产出物一律写到新副本，绝不改动模板/数据源原文件。
> 架构按 `11409` 需求文件设计，数据源角色统一命名（见 `zconfig.constant.py`）。

---

## 一、数据源角色（按 11409 需求）

| 角色 | 文件 | 形态 | 用途 |
|------|------|------|------|
| **A** | `xlsm/.xlsx_dataSource` | .xlsx 数据文件（**只读第一个工作表 Sheet0**，其余忽略） | ① 第 1 列有色单元格 → **分组**；② 经 col_mapping 取数 → **部分待填列数据** |
| **B** | `xlsm/.xlsm_template_base` | .xlsm 基础模板 | 已填部分数据列 → 分析得到「**已填列**」 |
| **C** | `xlsm/.xlsm_template_complete` | .xlsm 完整模板 | 完整列即产出参照 → 分析得到「**完整列**」 |
| **M** | `xlsm/.xlsx_dataSource_m.json` | JSON 自定义数据源 | 补充 A 映射**未覆盖到**的剩余待填列数据（值数组可含空串 `""`） |
| **D** | `outputs/fr_shirt_filled.xlsm` | .xlsm 产出 | 🎯 最终产出 = 模板 B 副本 + 按 plan 填充 |

> 角色关系：**C − B = 待填列范围（col_scope）**；**待填列数据 = A（映射部分）+ M（剩余部分）**；D = B 副本 + 填充结果。

---

## 二、端到端流程图（数据源 → 最终产出物）

```
┌─────────────────────────────────────────────────────────────────────┐
│  ③ 完整模板 C（.xlsm_template_complete）   ② 基础模板 B（.xlsm_template_base）│
│     完整列 = 产出参照                          已填列 = 基础                │
└───────────────────┬──────────────────────────────┬────────────────────┘
                    │ analysisXlsm.py ①            │ analysisXlsm.py ①
                    ▼                              ▼
            completed.json ◄─────────────►  blank.json
                    └───────────┬──────────────────┘
                                ▼
                      column_diff.py ②
                                │
                                ▼
              column_diff.json  ←  C − B = only_in_completed = 待填列范围(col_scope)
                                 settings.dataRow = 唯一真源（供 ⑤⑥ 偏移用）
                                │
        ┌───────────────────────┼───────────────────────────┐
        ▼                       ▼                           ▼
 build_groups_from_excel.py ③   │                  build_data_from_excel.py ④
 输入：数据源 A（.xlsx_dataSource）│                  输入：数据源 A × col_mapping
 规则：A 列有色单元格 = 父体锚点    │                  规则：按映射取非空值序列
 （存实际行号，无偏移）           │                  （按 groups 实际行号直接读）
        │                       │                           │
        ▼                       ▼                           ▼
 groups.json（实际行号）    data_start_row ───────►  data.json   +   col_mapping.json（人工维护）
        │        （只流向 ⑤⑥ 的偏移，不参与分组）          │                    │
        │                                   └──────┬─────────────┘
        │                                          ▼
        │                              M 数据源（.xlsx_dataSource_m.json）──┐
        │                                          │（补充 A 未映射列）       │
        └──────────────────┬───────────────────────┴───────────────────────┘
                           ▼
              build_fill_framework.py ⑤（合并 A 数据 + M 数据 → plan；data_start_row 读不到即报错）
                           │
                           ▼
        fill_plan/fr_shirt_fill_framework.json  ← 填充计划（可手工微调）
                           │
                           ▼
              fill_from_plan.py ⑥（模板 B 只读，写副本；填充时 +data_start_row−1 偏移）
                           │
                           ▼
        outputs/fr_shirt_filled.xlsm  ← 🎯 最终产出物 D（+ 可选 report.json）
```

---

## 三、脚本清单（按执行顺序）

| # | 脚本 | 输入 | 输出 | 职责 |
|---|------|------|------|------|
| ① | `analysisXlsm.py` | 任意 .xlsm（**B** 或 **C**） | blank.json（解析 B）/ completed.json（解析 C） | 解析 `Modèle` 表头 + `Valeurs valides` 可选值 → 列清单 JSON |
| ② | `column_diff.py` | completed.json + blank.json | `intermediate/<类别>/<类别>_column_diff.json` | **C − B** = 待填列；`settings.dataRow` 唯一真源 |
| ③ | `build_groups_from_excel.py` | 数据源 **A**（`.xlsx_dataSource`） | `<类别>_groups.json` | A 列有色锚点 → 分组行范围（**实际行号，无偏移**） |
| ④ | `build_data_from_excel.py` | 数据源 **A** + groups.json + col_mapping.json + column_diff.json | `<类别>_data.json` | 按分组 + 列映射取 A 的非空值序列 |
| ⑤ | `build_fill_framework.py` | column_diff/completed/blank/groups/data + **M 数据源 JSON** | `fill_plan/<类别>_fill_framework.json` | 汇总生成 plan（**A 数据 + M 数据合并**） |
| ⑥ | `fill_from_plan.py` | plan json | `outputs/*.xlsm`（可 `--report`） | 按 plan 写模板副本 + 清理多余空行 |

> 所有脚本的默认路径都来自 `zconfig.constant.py`（唯一配置真源），直接 `python <脚本>.py` 即可运行；参数均可覆盖。

---

## 四、各脚本详解

### ① `analysisXlsm.py` — 模板 → 列清单 JSON（只读）

- 解析两份工作表：
  - **`Modèle`**：row1 的 `settings=...` 串带出 `labelRow`(表头行，默认4) / `attributeRow`(属性键行，默认5) / `dataRow`(数据起始行，默认7)；按列收集 表头 / 属性键 / 示例数据。
  - **`Valeurs valides`**：第1列=分组标题，第2列=字段名（形如 `Type de produit - [ ]`），第3列起=可选值。
- 表头文本归一化后与字段名匹配；命中则 `matched=true` 并带 `choices` 枚举，否则视为自由文本列。
- 默认解析 **基础模板 B** → blank.json；解析 **完整模板 C** 得到 completed.json：

  ```bash
  python analysisXlsm.py                                    # B → blank.json
  python analysisXlsm.py xlsm/.xlsm_template_complete -o intermediate/fr_shirt/fr_shirt_completed.json
  ```

### ② `column_diff.py` — 找"该填哪些列"（C − B）

- 以列号 `col` 为唯一标识对比 completed（C 分析）/ blank（B 分析）：
  - `only_in_completed`：**C 有、B 没有 → 这就是要填的列（col_scope）**；
  - `only_in_blank`：B 有、C 没有（正常应为 0）。
- 同时按 `attribute` 再出一份差异，便于人工核对。
- 输出中携带模板标准 `settings`（labelRow/attributeRow/dataRow），**data_start_row 唯一真源 = 本文件的 settings.dataRow**（不同模板可能不同）；后续 build_fill_framework 写入 plan、fill_from_plan 填充时应用。**读不到则报错退出，不做兜底**。

### ③ `build_groups_from_excel.py` — 分组（父体 + 子体行范围，无偏移）

- 输入数据源 **A** 第 1 列，**有可见背景填充色的单元格 = 父体锚点行**（与 `services/utils.py` 的 `cell_has_fill` 逻辑一致）。
- **只读第一个工作表（Sheet0）**，其余工作表忽略。
- 每个锚点行 = 一个组的起始行；组结束行 = 下一锚点行 − 1；最后一组结束于 A 的 `max_row`。
- **分组无偏移**：groups 直接存 A 的实际行号：`"group_1": "start & end"`（如 `"1 & 19"`）；
  偏移（data_start_row）只在填充数据时由 fill_from_plan.py 应用。
- 示例：A 有 26 行、锚点在 1、20 → `{"group_1": "1 & 19", "group_2": "20 & 26"}`。

### ④ `build_data_from_excel.py` — 取数（A 部分）

- 输入：`groups.json`（实际行号）+ `col_mapping.json` + 数据源 **A**（**只读第一个工作表 Sheet0**，其余忽略；`--sheet` 可显式指定）。
- 列映射格式（`<类别>_col_mapping.json`，**人工维护**）：

  ```json
  { "sources": [ { "name": "excel_01",
      "mapping": { "K": ["BY","BZ"], "N": ["EG","HA"], ... } } ] }
  ```
  - 键 = 源 excel 列字母，值 = 目标列字母数组；**一对多 = 同一份数据复制到多个目标列**；映射应用到全部分组。
- 对每个分组、每个源列，在其行范围内逐行读**非空值**序列：`{ "data": { "<group>": { "<目标列号>": [值序列] } } }`

### ⑤ `build_fill_framework.py` — 汇总 → plan（含 M 合并）

把前面所有过程 json 汇总成一份完整的填充计划，**并合并 M 数据源**：

- **M 数据（`xlsm/.xlsx_dataSource_m.json`）** 支持两种形态：
  - **按组**：`{ "data": { "<group>": { "<目标列>": [值...] } } }`
  - **全局**：`{ "<目标列>": [值...] }` —— 同一份数据应用到全部分组
- **合并规则**（需求语义）：A 已有的列优先，**M 只补 A 未映射到的空缺列**；
  M 值数组允许空串 `""`（需求：m 包含空数据，空串也算一项，参与 fill_from_plan 的模式判断）。
- plan 字段一览：

  | plan 字段 | 来源 |
  |-----------|------|
  | `source_file` / `template_file` | completed（C）/ blank（B）分析 JSON 的 source_file |
  | `output_file` | 输出占位（默认 `outputs/fr_shirt_filled.xlsm`） |
  | `data_start_row` | column_diff.json 的 `settings.dataRow` |
  | `col_scope` | column_diff 的 only_in_completed 全部列号（升序） |
  | `mode_customise` | 空 `{}`，人工指定某列强制模式（**键 = 列字母**，如 `{"Q": "cycle"}`） |
  | `groups` | groups.json 的分组行范围 |
  | `cycle_threshold` | `null`（循环填充阈值） |
  | `data` | A 取数 + M 数据合并结果；均缺失则按 col_scope 填 `[]` 占位 |

**未覆盖列的两种收口（本脚本内的两个不变量）**：

1. **有可选值列必须由 AI 选满**（`⑦ ai_pick_attributes.py` 负责）：
   `col_scope` 中 A 未映射、且 completed 里有 `choices` 的列，只要还有「组×列」是占位
   （AI 没跑 / 只跑一半 / ⑥ 在 ⑦ 之后重跑把 M 里的 AI 结果覆盖回占位 / 回答值不在可选值内被拒），
   **打印明细并 exit 2、且不写 plan**，避免占位流进产出 Excel（⑦ 里也有同一道硬校验）。

2. **「A 未覆盖 且 无可选值」的目标列 → 指定值 / 多行值文件，整列连续循环**：
   目标列 = `uncovered_cols(diff, data)` − 有 `choices` 的列（`common.value_cycle_cols()`）。
   取值配置：`intermediate_tpl/column_defaults.json` 的当前类别分段（**键 = 列字母**，
   Excel 列名，大小写不敏感；兼容直接写列号）

   ```json
   { "yass_fr_coat": {
       "S":  { "value": "Coat-001" },
       "AT": { "file": "keywords_coat.txt" },
       "AN": { "value": "默认描述", "file": "colAN.txt" } } }
   ```

   - **`file` 优先于 `value`**；`file` 可写绝对路径 / 相对仓库根 / 纯文件名（到
     `antelope/values/<ACTIVE_CATEGORY>/` 下找）；文件不存在、读失败、为空 → 退回 `value`；
     两者都不行 → 该列**保留 `dataTemp` 占位**并在日志里列出（配置了但没值 vs 未配置分开提示）。
   - **序列填充**：指定值以数字结尾时自动递增——`"S-0001"` → `S-0001, S-0002, …, S-3027`
     （整列连续、跨组不重置；数字位数按种子左侧补零，如 `0001`/`A-1`）。
     `"sequence": false` 关闭（整列同值）；`"sequence": true` 强制（值必须以数字结尾，否则报错）；
     文件模式按行循环，不受 `sequence` 影响。
   - 值文件：每行一个值，`utf-8(sig)` / `gbk` 均可；**不允许空行**（出现空行 → exit 2 并给行号）。
   - **填充语义：不考虑分组**——数据区第 k 行取 `values[(k−1) % m]`，跨组不重置。
     实现是「按组旋转切片」写进 `plan.data`（切片长度恰等于组行数 → ⑥ 判定 `m == n` →
     sequential 顺序写入），因此 **`fill_from_plan.py` 无需任何改动**。
   - 配置了但不在目标集合的列（有 A 映射 / 有可选值 / 不在 col_scope）→ 跳过并说明原因，**不覆盖真实数据**；
     被 `mode_customise` 指定为 `children_only` 的目标列会与循环错位 → 跳过并提示二选一。

### ⑥ `fill_from_plan.py` — 按 plan 填充模板副本（最终产出 D）

- 模板 B 只读：`load_workbook(template, keep_vba=True)` 后写入 **`Modèle`** 工作表，另存为新文件。
- 行号语义：plan.groups = **实际行号（无偏移）**；填充到模板时应用偏移
  `target 行 = 分组行 + (data_start_row − 1)`，其中 data_start_row 来自 plan（源头 = column_diff.json 的 settings.dataRow）。
- **m = 该列数据数组长度（含空串 `""`）**，n = 组行数，自动判断填充模式：

  | 条件 | 模式 | 行为 |
  |------|------|------|
  | `m == 0` | none | 不填 |
  | `m == n` | sequential | 顺序填满父+子 |
  | `m == n − 1` | children_only | 只填子体（跳过父体行） |
  | `m < n` 且未超 cycle_threshold | cycle | 循环铺满（含空串占位） |
  | 其他 | mismatch | 不填，记入报告 |

  > `mode_customise` 可强制 `"sequential"` / `"children_only"` / `"cycle"`（配置文件 `intermediate_tpl/mode_customise.json`，
  > **键 = 列字母**，大小写不敏感，如 `{"yass_fr_coat": {"Q": "cycle"}}`；与 `column_defaults.json` 同一套写法）。
- **col_scope 守门**：data 里出现的列若不在 col_scope 内 → 默认跳过并 warn；`--strict-scope` 则报错退出。
- 填充完成后**清理模板多余历史行**：删除 `max_filled_row+1` 及之后的所有行。
- **父体行额外动作**（`parent_actions.py`，在删行之后、保存之前执行一次）：
  `intermediate_tpl/parent_actions.json` 按当前类别分段配置，**空配置 = 完全不动**：

  ```json
  { "yass_fr_coat": {
      "set_values":   { "D": "Parent" },
      "row_fill":     { "color": "FFFF00", "columns": null },
      "clear_values": { "columns": [] } } }
  ```

  - 父体行 = 每组**起始行**（实际行号 = 起始行 + `data_start_row − 1`），不会被删行波及；
  - `set_values`：把父体行**指定列改成固定值**（可多列；值可为文本/数字/布尔；以 `=` 开头会被当公式）；
  - `row_fill`：整行加**静态背景色**（真正的单元格填充，不是选中/阅读模式那种点击即消失的高亮）；
    `columns` 为 `null`/`"all"` → 整行（到模板最后一列），也可写 `"A:AW"` 或 `["A","B"]`；
  - `clear_values`：清除该行**指定列的值**（只清 value，不动格式）；
  - 执行顺序 `clear_values → set_values → row_fill`，同列既清又设时以 `set_values` 为准并告警；
  - 颜色/列写法非法 → 报错 `exit 2` 且**不写出产出**；执行明细写入 `--report`。
- 输出：默认 `outputs/result_filled.xlsm`（`-o` 传目录时自动补文件名）；`--report out.json` 可导出逐组逐列报告。

---

## 五、中间产物与最终产出物清单（fr_shirt 实例）

| 文件 | 生成脚本 | 内容 |
|------|----------|------|
| `intermediate/fr_shirt/fr_shirt_blank.json` | ① analysisXlsm（对 **B**） | 基础模板 B 的列：表头/属性键/可选值 |
| `intermediate/fr_shirt/fr_shirt_completed.json` | ① analysisXlsm（对 **C**） | 完整模板 C 的列（同上结构） |
| `intermediate/fr_shirt/fr_shirt_column_diff.json` | ② column_diff | C − B 的待填列（only_in_completed）+ settings（dataRow=8） |
| `intermediate/fr_shirt/fr_shirt_groups.json` | ③ build_groups_from_excel（对 **A**） | 分组：`1 & 19`、`20 & 26`（实际行号，无偏移） |
| `intermediate/fr_shirt/fr_shirt_col_mapping.json` | 人工维护 | A 源列→目标列映射（B→A、C→E、K→BY,BZ…） |
| `intermediate/fr_shirt/fr_shirt_data.json` | ④ build_data_from_excel（对 **A**） | A 部分：每组每列非空值序列 |
| `xlsm/.xlsx_dataSource_m.json` | 人工维护（**M**） | M 部分：补充列数据（可含空串） |
| `intermediate_tpl/column_defaults.json` | 人工维护 | 目标列（A 未覆盖且无可选值）取值：`value` / `file`（多行值文件，见 `values/<类别>/`） |
| `fill_plan/fr_shirt_fill_framework.json` | ⑤ build_fill_framework | 完整填充计划（col_scope + groups + A∪M 数据） |
| `outputs/fr_shirt_filled.xlsm` | ⑥ fill_from_plan | 🎯 **最终产出物 D**（模板 B 副本 + 数据） |

---

## 六、关键约定

1. **模板/数据源永远只读**：所有脚本只写 `intermediate/`、`fill_plan/`、`outputs/` 下的新文件。
2. **角色命名**：A → `xlsm/.xlsx_dataSource`、B → `xlsm/.xlsm_template_base`、C → `xlsm/.xlsm_template_complete`、M → `xlsm/.xlsx_dataSource_m.json`（统一在 `zconfig.constant.py` 声明）。
3. **列范围 = C − B**：col_scope 只含「完整模板 C 有、基础模板 B 没有」的列；data 里出现 col_scope 之外的列会被跳过（`--strict-scope` 可改为报错）。
4. **数据 = A + M**：A 经 col_mapping 取数；M 为 JSON，只补 A 未映射的列；A 已有列优先。
5. **m 包含空数据**：plan.data 数组里的 `""` 算一项，直接影响 sequential / children_only / cycle 的模式判断。
6. **data_start_row 唯一真源** = `column_diff.json` 的 `settings.dataRow`（由模板解析得到，不同模板可能不同）；由 ⑤ 写入 plan、⑥ 填充时应用。**读不到说明流程有问题（缺 column_diff 或 settings），直接报错，不做兜底**。
7. **行号语义**：plan/groups 中存**实际行号（无偏移）**；偏移只在填充数据时应用：`target 行 = 分组行 + (data_start_row − 1)`。
8. **新增类别/国家**：改 `zconfig.constant.py` 顶部的 `ACTIVE_CATEGORY`（如 `"fr_shirt"` → `"de_coat"`），所有默认路径自动切换，代码零改动。
9. **未覆盖列的归属只有三种，且各有硬约束**：① A 映射取数；② 有可选值列 → ⑦ AI 选值（**不允许残留占位，⑦⑧ 都会报错退出**）；③ 其余（A 未覆盖且无可选值）= **目标列** → `intermediate_tpl/column_defaults.json` 指定值/多行文件，整列连续循环；未配置的目标列才会在产出里留下 `dataTemp`（⑧ 日志会逐列列出）。
