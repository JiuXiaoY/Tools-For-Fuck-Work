# dealExcel_refactoring 问题清单

> 按优先级排序:P0=安全/致命, P1=架构/严重影响维护, P2=可维护性改善, P3=优化建议。
> 每个问题标注文件:行号,先不改动,仅记录。

---

## 🔴 P0 — 安全/致命

### 1. API 密钥硬编码在仓库中
- **文件**:`config.py:70`
- **内容**:`ai_api_key: str = "sk-39b17cf2e6a542508090bb1c8d07570d"` — 真实的 DeepSeek API 密钥
- **影响**:密钥已提交到版本控制,通过 git history 可被任何人获取。需立即轮换密钥并迁移到环境变量
- **对比**:`config.example.py:70` 正确使用了空字符串

---

## 🟠 P1 — 架构/严重影响维护

### 2. Config 注入形同虚设 — 11 处重复 `Config()`
- **涉及文件**:所有 `steps/*.py`(除 `finalize.py` 外 11 个步骤文件)
- **问题**:`core/runner.py:19` 接受 `Config` 参数传给 pipeline,但每个 `PipelineStep.run()` 内部都自己调 `Config()` 重新实例化,外部传入的配置**被完全忽略**
- **影响**:
  - 无法测试(无法注入 mock 配置)
  - 无法在单进程用不同配置处理不同文件
  - 步骤的依赖不透明(看代码不知道配置从哪来)
- **根因**:`PipelineStep` 没有 `__init__` 接收 Config

### 3. 两套步骤接口并存,互不兼容
- **核心 Pipeline**:`PipelineStep.run(ctx: PipelineContext) → PipelineContext`(`core/pipeline.py:15`)
- **预处理步骤**:`self.run(wb: Workbook, path: str) → int`(`preprocess/steps/dedup_filled_rows.py:30`)
- **问题**:同样的"步骤"概念,签名完全不同。预处理步骤不是 `PipelineStep` 子类,无法被核心 pipeline 调度,也无法共享日志/上下文机制
- **影响**:增加认知负担,两套注册表要分别维护

### 4. openpyxl 工作簿泄露 — `wb.close()` 缺失
- **`core/runner.py:21-32`**:`process_file()` → `load_workbook()` → 只 `save()` 不 `close()`
- **`services/excel.py:47`**:`merge_workbooks()` 打开源文件后不关闭
- **`services/excel.py:21-23`**:`save()` 不对 workbook 调用 `close()`
- **`main.py:69-70`**:`merge_workbooks()` + `save()` 后的 workbook 未关闭
- **正面例子**:`preprocess/run.py:40-44` 正确调用了 `save()` → `close()`
- **影响**:42MB 的 xlsx 文件不关闭,长期运行会累积内存/文件句柄

### 5. 三个 `except Exception: pass` 静默吞异常
- **`services/excel.py:75-76`**:合并单元格失败 → `pass`,不输出任何警告
- **`steps/merge_sheets.py:85-86`**:同上
- **`services/utils.py:47-48`**:`to_decimal()` 捕获所有异常返回 `None` — 其中包括 `KeyboardInterrupt` 和 `SystemExit`
- **`rules/price.py:21-22`**:`extract_price_before_jpy()` 同样问题
- **影响**:数据静默丢失不可追踪;`KeyboardInterrupt` 可能被吞掉导致进程无法退出

### 6. "重建 sheet"逻辑重复 × 3 — 代码量最大
- **文件**:`preprocess/steps/remove_header.py:56-104`、`dedup_filled_rows.py:77-166`、`remove_empty_j.py:44-131`
- **问题**:三段代码的模板完全一致:创建临时 sheet → 复制行(值+样式+图片+合并单元格+列宽) → 替换旧 sheet。唯一差异是"哪些行要删"的判定规则
- **影响**:约 200 行重复代码;修改复制逻辑(如增加一列样式属性)需要改三个地方
- **建议抽象**:`rebuild_sheet(ws, keep_predicate: Callable[[int], bool]) → Worksheet`

### 7. `jenkins.py` 用 `subprocess.run` 串步骤 — 多余进程边界
- **文件**:`jenkins.py:43-56`
- **问题**:每步都是一个独立 Python 子进程,通信全靠文件系统;当前 7 步中 5 步注释掉
- **影响**:
  - 步骤失败时只能看到"子进程返回非零",无堆栈
  - 每次子进程启动都要重新 import 全部模块
  - 无法在内存中传递中间状态
- **这些步骤完全可以改成进程内函数调用**

---

## 🟡 P2 — 可维护性

### 8. `config.example.py` 与 `config.py` 不同步
- **缺失字段**:`img_classify_mode`、`img_classify_ocr_lang`、`img_classify_table_min_lines`
- **默认值不一致**(5 处):`date_override`("260708" vs "260731")、`price_add`("6.00" vs "1.50")、`delete_source_after_merge`(True vs False)、`preprocess_dedup_close_gap`(10 vs 5)、`ai_api_key`(真实密钥 vs "")
- **节标题不同**:`image classification` vs `image reorder`
- **影响**:新用户按 example 模板创建 config 后,缺少 3 个配置字段会导致 AttributeError

### 9. `constant/` 目录 — 未使用的杂项数据,疑似敏感信息 **[已修复]**
- **文件**:`constant/dzq` 包含邮箱、品牌名、验证码等数据
- **状态**:无任何 Python 代码 import `constant/` 目录
- **`constant/photo/`**:4 个参考 PNG 图片,无代码引用
- **修复**:`constant/photo/`、`constant/dzq` 已加入 `.gitignore` 并从 git 跟踪移除

### 10. ID 生成逻辑硬编码 — 无扩展性
- **文件**:`steps/fill_id.py:10-29`
- **硬编码内容**:
  - 编码表:base62(`string.digits + ascii_uppercase + ascii_lowercase`)
  - 分段格式:`6 位前缀 + 6 位日期码 + 4 位后缀`(固定 16 字符)
  - 日期编码:`0→z, 1→a, ..., 9→i`
- **影响**:不同平台需要不同 ID 格式时,只能复制整个函数重写
- **建议**:做成可注入的 `Callable` 参数,当前不需要完整类层次

### 11. 价格计算公式硬编码
- **文件**:`steps/calc_price.py:27-30`
- **硬编码**:四步链 `AS=base, AT=base×1.2, AU=AT-7.98, AV=AU+1.50` — 乘数/减数/加数虽来自 config,但**步骤数量和顺序**写死在代码里
- **影响**:不同市场(含 VAT / 不含 VAT)需要不同计算链时无法配置
- **建议**:与 ID 生成同理,做成可注入的函数或公式字符串

### 12. 29 处 `time.sleep()` 硬编码
- **涉及文件**:`tools/title_optimize/run.py`(3 处模块常量)、`deepseek_web.py`(14 处硬编码)、`hotwords.py`(`REQUEST_INTERVAL=2.0`+ 2 处 0.5/3)、`hotwords_fashion.py`(`REQUEST_INTERVAL=2.0`+ 硬编码 3)、`image_classification/reorder*.py`(3 处 1s)
- **影响**:API 限流策略调整(如 amz123 改成 1s/次)需要改代码
- **config.py 现状**:有 `retry_max_rounds_*`,但无 `delay_*` 或 `interval_*`

### 13. `RemoveEmptyJStep` — 完整实现但注释掉
- **文件**:`preprocess/steps/remove_empty_j.py:1-147`(147 行完整实现)
- **注册**:`preprocess/steps/__init__.py:4,11` 两处注释掉
- **状态**:无其他引用,可能是死代码,也可能是未完工的功能
- **影响**:147 行代码占位但未使用

### 14. 图片 anchor 行号操作重复 × 2(以上)
- **核心流程**`merge_sheets.py` 和**预处理 3 个步骤**各自手写:
  ```python
  if isinstance(anchor, OneCellAnchor):
      old_row = anchor._from.row + 1
  elif isinstance(anchor, TwoCellAnchor):
      old_row = anchor._from.row + 1
  ```
- **`services/images.py`** 有 `snapshot_images` / `restore_images`,但没有封装"提取行号/平移 anchor"的通用函数
- **影响**:每次用到 anchor 都要重复判断;`services/excel.py:75`(merge_workbooks 内)也有一份

### 15. `services/excel.py` 使用 `logging.getLogger` 绕过项目日志系统
- **文件**:`services/excel.py:14`
- **问题**:项目统一用 `services/logger.py:get_logger()`,但 excel.py 直接用 stdlib `logging.getLogger(__name__)`,多个 handler/格式不一致

### 16. 无步骤级容错 — 部分失败即全部丢失
- **文件**:`core/runner.py:46-56`
- **问题**:Pipeline 12 步串行,没有任何 try/except 包裹单步;如果第 11 步失败,前 10 步的更改无法保存(workbook 只在所有步骤跑完后 save)
- **影响**:调试困难(无法查看失败时的中间状态);无法只重跑失败步骤

### 17. 无中间检查点
- 关联 #16:如果 Pipeline 支持"每完成 N 步存一个中间文件"或"保存 Context 到临时路径",长流程调试效率会高得多

### 18. 多层数据传递全靠文件系统
- **链路**:preprocess 写回源文件 → main 读源文件合并 → tools 读输出文件再加工再写回
- **问题**:每次 read/write openpyxl 都重新解析 42MB 的 xlsx;1000 行不明显,10 万行时是显著瓶颈
- **中间零内存传递**

### 19. `tools/image_classification/reorder_backup.py` — `reorder.py` 的 ~90% 重复副本
- **文件**:`reorder.py` 和 `reorder_backup.py` 高度相似
- **影响**:改一处不同步另一处,逐渐分化

### 20. `MergeSheetsStep` 未使用 `services/images.py` 的图片辅助
- **文件**:`steps/merge_sheets.py:54-84` 内联了图片复制的全部逻辑
- **问题**:`services/images.py` 有 `clone_image`,但 merge_sheets 自己的图片循环没用到,自己写了一份

### 21. `services/images.py:58` — `restore_images` 依赖整个 Config 对象
- **文件**:`services/images.py:58`
- **问题**:`restore_images` 只需要 `column_insertions: list[tuple[int,int]]`,却接收整个 `Config`,耦合了不必要的数据结构

### 22. 配置加载无缓存 — `load_color_mapping` / `load_size_mapping` 每次读磁盘
- **文件**:`config.py:106-120`
- **问题**:`FillCol10MappingStep` 和 `SizeMappingStep` 各自调用时都会重新 open+parse JSON
- **影响**:742 条 color_mapping.json + size_mapping.json 每次管道运行读 2 次磁盘

### 23. `tools/title_auto_fill/de_title_build.py:4` — TODO 标记未闭环
- **内容**:`# de_collect.py — populate final_de_title (TODO)`
- **影响**:自动化步骤不完整

### 24. 热词采集 fashion_brands.txt 首行追加丢失 bug(已修复但原因不明)
- **文件**:`tools/needToCollect/fashion_filter/fashion_brands.txt`
- **问题**:bash heredoc 追加时 `geox` 首行丢失,原因未知(可能 Windows 换行符问题)
- **已修复**:通过 Python 工具 edit_file 补回
- **影响**:说明基于 bash heredoc 的文件追加在 Windows 下不可靠

---

## 🟢 P3 — 小改进

### 25. `deepseek_web.py` 的选择器硬编码
- **问题**:`button:has-text('Stop')`、`"div.ds-assistant-message-main-content"` 等 CSS 选择器与 DeepSeek UI 版本绑定
- **影响**:DeepSeek 页面改版后需手动同步选择器;无版本兼容机制

### 26. 项目日志系统仅一处不一致
- **文件**:`services/excel.py:14` 用 `logging.getLogger(__name__)` 而非 `get_logger("excel")`
- **影响**:细微不一致,Excel 模块日志可能丢失项目级的格式/级别配置

### 27. `services/logger.py:26-27` — 模块级全局状态
- **内容**:`_log_file: Path | None = None`, `_initialized: bool = False`
- **影响**:正式单线程使用无问题,但多人协作或多线程时会成为隐式竞争

### 28. `core/pipeline.py` — Pipeline 无步骤排序/依赖验证
- **问题**:12 步的注册靠 `get_steps()` 里的硬编码列表顺序,每步间有隐式数据依赖(如 InsertColumns 必须先于列引用)但未声明
- **影响**:加新步骤时容易放错位置

### 29. 缺少统一的 CLI 入口
- **现状**:`main.py` 无参数、`preprocess/run.py` 无参数、`jenkins.py` 硬编码步骤、各 tools 各有一套 argparse
- **影响**:用户需记住多个入口点,无法 `dealexcel pipeline --steps 1-5`

### 30. 缺少测试
- **状态**:整个项目无任何 test_*.py 文件
- **影响**:重构和修改配置逻辑时无安全网;商业化接客户前需手工回归

### 31. 缺少类型检查 CI
- **现状**:有 `from __future__ import annotations` + 类型注解,但无 `mypy`/`pyright` 配置和 CI 检查
- **影响**:类型注解失去约束力,实际运行时可能类型不匹配

### 32. `main.py` 异常处理把临时文件删除和重新抛混在一起
- **文件**:`main.py:83-86`
- **问题**:`except Exception as exc: tmp.unlink(missing_ok=True); raise` — `KeyboardInterrupt` 等非 Exception 异常不会被此 except 捕获(try/except Exception),但 `SystemExit` 会?不会。逻辑正确性没问题,但意图不明确(是只处理预期错误还是兜底?)

### 33. `.gitignore` 缺 `constant/photo/` 和 `constant/dzq` **[已修复]**
- **修复**:`constant/photo/`、`constant/dzq` 已加入 `.gitignore`,`constant/photo/` 下 4 个 PNG 和 `constant/dzq` 已从 git 跟踪移除(`git rm --cached`)

### 34. `fashion_filter` 的弱属性 `wolle` 有历史重复(强属性段 `!wolle` 残留)
- **已修复**:`fashion_attributes.txt:17` 的 `!wolle` 已删除
- **教训**:同一词在强/弱两段各出现一次,copy-paste error 的典型案例

### 35. 三个预处理步骤的输出目录不同
- `remove_header` 输出 `_rm_header_tmp` 临时 sheet
- `dedup_filled_rows` 输出 `_dedup_tmp`
- `remove_empty_j` 输出 `_rm_empty_j_tmp`
- **问题**:命名不统一,如果多个临时 sheet 同时存在时会冲突(实际先 remove 再 create,不冲突,但可读性差)

---

## 统计

| 优先级 | 数量 |
|---|---|
| 🔴 P0 | 1 |
| 🟠 P1 | 6 |
| 🟡 P2 | 17 |
| 🟢 P3 | 11 |
| **合计** | **35** |
