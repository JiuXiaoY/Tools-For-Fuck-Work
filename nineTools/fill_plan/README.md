# fill_from_plan —— 把 data 按「填充计划」写入模板

只读模板，写**新副本**；填哪列、填哪些值、按什么顺序，全部由 **plan JSON** 描述，程序本身不硬编码任何列。

## 文件
- `fill_from_plan.py`：核心填充器。
- `fill_plan/example_fill_plan.json`：示例 plan，可直接跑、演示四种规则。

## 用法
```bash
python nineTools/fill_from_plan.py nineTools/fill_plan/example_fill_plan.json --report outputs/report.json
```
`template_file` 与 `output_file` 都在 plan 里写明；`--report` 可选，输出逐组逐列的填写结果。

---

## Plan JSON 结构

| 字段                | 类型                    | 说明                                                               |
|-------------------|-----------------------|------------------------------------------------------------------|
| `template_file`   | str                   | 只读模板路径（.xlsm）                                                    |
| `output_file`     | str(可选)               | 输出副本路径；缺省为模板同目录下 `<模板名>_filled.xlsm`                             |
| `data_start_row`  | int                   | 模板数据起始行。**组内行号按"数据区第1行=1"计**，实际模板行 = 组内行号 + `data_start_row - 1` |
| `col_scope`       | int[]                 | 允许填写的**列号集合（非连续）**。不在其中的列，无论 data 里有没有都**绝不写**                   |
| `groups`          | {name: "start & end"} | 分组。`start`=该组父体所在行，`end`=末个子体行（窗口坐标）                             |
| `cycle_threshold` | int 或 null            | 循环阈值，见下                                                          |
| `data`            | {name: {列号: [值,...]}} | 每组每列填充数据；列号为字符串形式                                                |

```json
{
  "template_file": "prompt_fr/final_init_template/coat_template_Eva.xlsm",
  "output_file": "outputs/filled.xlsm",
  "data_start_row": 7,
  "col_scope": [1, 2, 4, 12, 17, 21, 40, 133],
  "groups": { "group_1": "1 & 99", "group_2": "100 & 199" },
  "cycle_threshold": null,
  "data": {
    "group_1": { "12": ["值1", "值2"], "133": ["500", "600"] }
  }
}
```

---

## 每列填充规则

设该组**数据行数 = n**（= end - start + 1），该列**数据条数 = m**：

| 条件 | 行为 | mode |
|---|---|---|
| `m == 0` | 不填 | `none` |
| `m == n` | 按顺序填满整组（父体+所有子体） | `sequential` |
| `m == n - 1` | 只填**子体**（跳过父体那一行，从第 2 行开始） | `children_only` |
| `0 < m < 阈值` | **循环铺满**整组行（第 i 行取 `values[i % m]`） | `cycle` |
| 其它（`m > n`，或阈值禁用了循环但仍小于 n） | 不写，记为 `mismatch`，写入报告 | `mismatch` |

> `cycle_threshold = null` 时，任何 `0 < m < n` 都按循环处理。
> 设为具体整数时，只有 `0 < m < cycle_threshold` 才循环，其余落入 `mismatch`。

## 列范围与安全

- 只写入 `data_start_row` 之下、落在 `groups` 范围内的行。
- 只写入 `col_scope` 内的列；data 中出现但不在 scope 的列会被**跳过并警告**（`--strict-scope` 可改为报错退出）。
- 模板始终只读，绝不回写；产出是独立副本。
