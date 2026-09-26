# 当前问题与技术债

本文件只记录当前代码中仍存在的问题。已经修复的历史问题不继续保留，避免状态与代码脱节。

## P0：安全与数据完整性

### 1. 仓库中存在疑似真实凭据

- `config.example.py` 包含看起来像真实 API Key 的默认值。
- 历史问题文档曾直接记录完整密钥；本文件不再保留其值。
- 已跟踪的 `zip_by_ec/Tools_refactoring_completed.zip` 内含 `config.py` 和 `.git/config`。

建议：立即轮换相关凭据，清理当前版本和 Git 历史，并给打包流程增加白名单。

### 2. `.xls` 转换脚本只改扩展名

`tools/xls2xlsx.py` 使用 `Path.rename()` 把 `.xls` 改成 `.xlsx`，没有转换文件格式。真实 BIFF `.xls` 不能因此被 `openpyxl` 读取。

建议：先识别文件签名；真实 `.xls` 使用 Excel COM、LibreOffice 或专用转换方案，成功后再移动原文件。

### 3. 主流程可能同时丢失输入和输出

`main.py` 在 `process_file()` 成功前删除源文件，异常分支又会删除临时输出。

建议：处理到临时文件，完成强校验并原子发布后，再把输入移动到可恢复的归档目录。

## P1：正确性与流程边界

### 4. 输入和输出校验只写日志

`steps/validate.py` 与 `steps/finalize.py` 不会在列数或关键结构错误时失败，错误数据仍可能被发布。

建议：为关键列数、必要表头、目标工作表、图片数量和输出格式定义硬校验。

### 5. `continue_on_error` 不处理依赖失败

前置步骤失败后，`core/runner.py` 仍可能执行依赖该步骤的后续步骤，导致数据写入错误列位。

建议：记录失败步骤并跳过所有依赖它的步骤；生产模式默认保持 fail-fast。

### 6. 运行数据和源码混在同一目录

浏览器状态、批次 JSON、日志、模板、输出和压缩快照占据大量空间。仅 `antelope/fill_plan` 与 `antelope/intermediate` 中被跟踪的生成数据就接近 180 MB。

建议：运行态数据集中到一个整体忽略的目录；Git 只保存源码、少量标准配置和无法重建的资源。

### 7. 打包工具没有排除规则

`nineTools/zip/zip_dir.py` 会递归打包所有文件，可能包含 `.git`、`config.py`、浏览器 Cookie 和缓存。

建议：改成明确白名单，或使用 `git archive` 只导出已跟踪且允许发布的文件。

### 8. 缺少 Excel 回归测试

当前没有有效的自动化测试。图片、合并单元格和宏依赖 openpyxl 的实现细节，修改后只能人工确认。

建议建立小型黄金文件，覆盖单工作表、多工作表、合并单元格、图片锚点、32→49 列和异常回滚。

## P2：可维护性

### 9. 列变量的名称与真实 Excel 列已经错位（已修复）

增加列后遗留的 `col_i`、`col_j`、`col_ar` 等旧名称已改为业务名称；列号和 49 列布局保持不变。

当前使用 `source_color_col`、`mapped_color_col`、`size_col`、`price_source_col` 和价格链业务名称。

### 10. `copy_targets` 注释与实现方向相反

`config.example.py` 写成 `{source_col: target_col}`，`steps/copy_mirror.py` 实际按 `{target_col: source_col}` 使用。

### 11. `id_factory` 类型与实现不一致

配置声明为 Callable，`steps/assign_ids.py` 却把它当字符串注册名解析。注入 Callable 时会退回默认工厂。

### 12. 依赖声明不完整

`pyproject.toml`、`requirements.txt` 和真实工具依赖不一致。Playwright、AI SDK、NumPy、OpenCV 等没有清晰的可选依赖分组。

建议增加 `ai`、`browser`、`vision`、`dev` 等 optional dependency groups。

### 13. 大量使用 openpyxl 私有接口

图片逻辑依赖 `_images`、`_from`、`_data()` 等私有成员，升级 openpyxl 时可能破坏兼容性。

建议锁定版本，并通过集中适配层和黄金文件测试隔离风险。

### 14. 部分工作簿生命周期不清晰

`services/excel.merge_workbooks()` 打开的源工作簿没有逐个关闭；`process_file()` 返回的 Context 又引用已经关闭的 Workbook。

### 15. 主流程、antelope 与独立工具缺少统一入口

目前需要记忆多个脚本路径，部分编排仍依赖注释代码来控制步骤。

建议逐步提供统一 CLI，例如 `dealexcel pipeline`、`dealexcel antelope`、`dealexcel hotwords`，同时保留底层脚本入口。
