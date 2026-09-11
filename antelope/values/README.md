# antelope/values —— 目标列的「多行值文件」目录

`intermediate_tpl/column_defaults.json` 里给某列配 `"file"` 时，值文件放在这里：

```
antelope/values/<ACTIVE_CATEGORY>/keywords_coat.txt      # 配置里写 "file": "keywords_coat.txt"
                                                         # 该列在配置里用列字母作键，如 "AT"
```

规则：

- **每行一个值**，按行顺序循环填满该列（数据区第 1 行取第 1 行，到底回到开头，跨组不重置）；
- 编码 `utf-8` / `utf-8-sig` / `gbk` 均可，文件末尾的换行不算一个值；
- **不允许空行**：出现空行会直接报错并给出行号（值文件按约定不含空值）；
- 文件不存在 / 读失败 / 为空 → 退回该列配置的 `value`；都没有 → 保留 `dataTemp` 占位。

本目录随仓库入库（人工维护，与 `col_mapping.json` 同类）。
