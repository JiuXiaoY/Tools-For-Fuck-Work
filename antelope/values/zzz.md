# antelope/values —— 目标列的「多行值文件」目录

值文件按 `<国家>_<性别>/` 存放。国家使用站点代码 `de`、`fr` 或 `uk`，性别沿用文件名中的 `Adam`（男款）、`Eva`（女款）、`Uni`（通用）。没有性别标记的文件归到对应国家的 `unknown`。

文件名省略账号，例如 `de_Adam/de_tracksuit_Adam.txt`。同名文件保留有效数据行数更多的一份，使用统一文件名。带 `.orig` 等备份标记的文件从值文件目录移除。

在 `intermediate_tpl/column_defaults.json` 中，`file` 填相对 `values/` 的路径，如 `"file": "fr_Eva/fr_coat_Eva.txt"`。

写相对路径时依次查找：

1. `antelope/values/<file>`
2. `<仓库根>/<file>`
3. 相对当前工作目录的 `<file>`

（写绝对路径则直接用该路径；都没找到时会在日志里列出实际找过的路径。）

规则：

- **每行一个值**，按行顺序循环填满该列（数据区第 1 行取第 1 行，到底回到开头，跨组不重置）；
- 编码 `utf-8` / `utf-8-sig` / `gbk` 均可，文件末尾的换行不算一个值；
- **不允许空行**：出现空行会直接报错并给出行号（值文件按约定不含空值）；
- 文件不存在 / 读失败 / 为空 → 退回该列配置的 `value`；`value` 也空 → 保留 `dataTemp` 占位。

本目录随仓库入库（人工维护，与 `col_mapping.json` 同类）。
