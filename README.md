# dealExcel_refactoring

> Excel 批量处理流水线 — 32 列 → 48 列，一键从 .xls 到优化输出

---

## 快速开始

```bash
pip install -r requirements.txt

# 可选：安装为命令行工具（pyproject.toml 提供 dealexcel 命令）
pip install -e .

# 创建配置文件（复制模板后填入密钥；config.py 已被 .gitignore，不会入库）
cp config.example.py config.py

# 放入 .xls 到 public/xls_src/，然后：
python jenkins.py
```

输出：`outputs/{日期}v{版本}.xlsx`（同日多次运行自动递增 v1、v2、v3…）

---

## 目录结构

```
dealExcel_refactoring/
│
├── jenkins.py                  # 一键启动全流程（STEPS 列表可编辑，见下文）
├── main.py                     # Excel 流水线入口（多文件合并 + 12 步流水线）
├── config.py                   # 所有配置（config.example.py 是模板）
├── requirements.txt / pyproject.toml   # 依赖 / 项目元数据
├── REFACTOR_GUIDE.md           # 重构指南
├── ISSUES.md                   # 问题与待办
│
├── core/                       # 流水线核心
│   ├── pipeline.py             #   PipelineStep 抽象基类（name / description / requires）
│   ├── runner.py               #   Pipeline 调度器（顺序校验、容错、检查点）+ process_file() 入口
│   └── context.py              #   PipelineContext（workbook / worksheet / metadata / logs）
│
├── steps/                      # 12 个流水线步骤（注册表 = steps/__init__.py 的 get_steps()）
│   ├── __init__.py             #   步骤顺序与 requires 依赖声明
│   ├── merge_sheets.py         #   ① 多 sheet 合并为一张（保留图片/样式/合并单元格）
│   ├── validate.py             #   ② 校验行列数
│   ├── insert_columns.py       #   ③ 按配置插入空白列（图片锚点同步平移）
│   ├── assign_ids.py           #   ④ B 列随机 16 位 ID（中间 6 位日期码；ID 工厂可配）
│   ├── cascade_identifier.py   #   ⑤ C 列级联填充（按 A 列填充色取 B 列，否则继承上一行）
│   ├── map_colors.py           #   ⑥ J 列颜色映射（未命中记入 data/to_be_completed.json）
│   ├── size_mapping.py         #   ⑦ K 列尺码映射（原地替换，有色行清空）
│   ├── copy_mirror.py          #   ⑧ 按 copy_targets 源列→目标列镜像复制
│   ├── mirror_category.py      #   ⑨ AR 列 ← L 列
│   ├── calc_price.py           #   ⑩ AS-AV 价格链计算（JPY 锚定提取基数）
│   ├── format_cells.py         #   ⑪ 行高 / 对齐 / 列宽 / E 列 =LEN(D) 公式
│   ├── finalize.py             #   ⑫ 输出最终行列数
│   └── remove_header.py        #   （旧版未注册，仅存档；去表头请用 preprocess/）
│
├── preprocess/                 # 预处理（在 public/xls_xlsx/ 原始文件上原地修改，流水线之前）
│   ├── run.py                  #   入口
│   └── steps/
│       ├── remove_header.py    #     去表头（A1 无填充色则删除首行）
│       ├── remove_empty_j.py   #     移除 J 列空的无色行（config 开关控制）
│       ├── dedup_filled_rows.py#     SKU 去重（按填充色锚点 + 间距阈值）
│       └── rebuild.py          #     重建工作表工具（删行后图片/样式/合并单元格重排）
│
├── services/                   # 工具函数
│   ├── excel.py                #   load / save / merge_workbooks（多文件合并）
│   ├── images.py               #   图片快照 / 恢复 / 克隆（插列、合并时保持锚点）
│   ├── preserver.py            #   ZIP 级素材保全（media / Content_Types）
│   ├── unmapped.py             #   未映射颜色/尺码记录 → data/to_be_completed.json
│   ├── utils.py                #   单元格工具（is_blank / cell_has_fill / round_decimal）
│   ├── ai_client.py            #   AI 客户端注册表（gemini / deepseek，可扩展）
│   └── logger.py               #   统一日志（logs/ 同日复用）
│
├── rules/                      # 业务规则
│   └── price.py                #   价格提取（取 JPY 前的那个价格）
│
├── data/                       # 映射表
│   ├── color_mapping_de.json   #   颜色 英→德
│   ├── color_mapping_fr.json   #   颜色 英→法
│   ├── size_mapping_de.json    #   尺码映射 (德)
│   ├── size_mapping_fr.json    #   尺码映射 (法)
│   ├── dress_attributes_options_fr.json  # 法站连衣裙属性可选项知识库（供人工/AI 参考）
│   └── to_be_completed.json    #   未映射颜色/尺码待补清单（流水线自动追加）
│
├── tools/
│   ├── xls2xlsx.py             # .xls → .xlsx（public/xls_src/ → public/xls_xlsx/）
│   ├── txt2md.py               # .txt → .md（public/txt_src/ → public/txt_md/）
│   ├── needToCollect/          # 热词采集
│   │   ├── needToCollect.md    #   关键词输入文件（每行一个）
│   │   ├── hotwords.py         #   采集程序（amz123 API；--country / --single）
│   │   ├── cleaner.py          #   清洗管道
│   │   ├── base_words/         #   基础词库（de/fr 分目录）
│   │   ├── result/             #   采集输出（gitignored）
│   │   └── fashion_filter/     #   服装热词采集+清洗（一条龙）
│   │       ├── hotwords_fashion.py    #   主程序：采集 → 留存原始 raw/ → 清洗 → 留存结果 result/
│   │       ├── clean_fashion.py       #   清洗逻辑：品类词根/强弱属性/黑名单/品牌移除
│   │       ├── fashion_categories.txt #   服装品类词根（只保留穿在身上的衣服）
│   │       ├── fashion_attributes.txt #   属性词根（! 前缀=强属性可独立保留，否则须搭品类词）
│   │       ├── fashion_excludes.txt   #   黑名单（明确非服装噪声）
│   │       ├── fashion_brands.txt     #   品牌表（token 级移除任意位置的品牌）
│   │       ├── raw/                   #   清洗前原始数据（gitignored）
│   │       └── result/                #   清洗结果（gitignored）
│   ├── color_size_deal/        # 颜色尺码处理
│   │   ├── color_reprocess.py  #   Excel → check_.txt → process.py 处理 → 回写第 10 列
│   │   ├── process.py          #   手动处理 check_.txt（组内重复前缀编号 + 去尺码列）
│   │   └── check_.txt          #   中间产物（gitignored）
│   ├── title_optimize/         # 标题优化（DeepSeek 网页自动化为主）
│   │   ├── title_rewrite.py    #   编排：提取(H→origin_title, O→origin_link) → 校验 → 优化 → 回写
│   │   ├── deepseek_web.py     #   DeepSeek 网页自动化（playwright，登录态保存复用）
│   │   ├── run.py              #   API 模式（图片 + 原标题 → AI 优化，可切 gemini/deepseek）
│   │   ├── download.py         #   图片下载
│   │   ├── origin_link / origin_title / optimize_title   # 中间产物（gitignored）
│   │   └── temp_photo / browser_data / deepseek_state.json # 临时图/浏览器数据（gitignored）
│   ├── title_auto_fill/        # 标题自动填充（德语）
│   │   ├── de_title_build.py   #   编排器：collect → write back
│   │   ├── de_collect.py       #   采集（当前为占位，未实现）
│   │   ├── de_write_back.py    #   回写第 4 列 + 空值填上一行公式
│   │   ├── gemini_web.py       #   Gemini 网页登录会话（playwright）
│   │   └── final_de_title / final_de_title_s  # 中间产物（gitignored）
│   ├── image_classification/   # 图片分类 & 重排（尺码表检测）
│   │   ├── classify.py         #   三引擎分类器（heuristic / ocr / opencv，可多引擎投票）
│   │   ├── reorder.py          #   逐行扫描重排（O-W 列 15-23，多线程）
│   │   ├── reorder_batch.py    #   批次重排（按 A 列有色行分组）
│   │   ├── reorder_backup.py   #   旧版备份
│   │   └── images_awaiting/    #   待处理图片（gitignored）
│   ├── export_sku/             # SKU 导出（前两列 → outputs/{日期} - N.xlsx）
│   │   └── export_sku.py
│   └── write_excel_temp/       # Excel 临时写表
│       ├── write_excel.py      #   生成示例 .xlsx
│       └── fill_az_from_help.py#   按 A 列有色分区循环写 AZ 列
│
├── antelope/                  # 填充计划生成工具（只读源、写新副本；详见 antelope/zzz.md）
│   ├── zconfig.constant.py     #   路径与配置唯一真源
│   ├── analysisXlsm.py         #   模板表头 + 可选值 → JSON
│   ├── column_diff.py          #   列差异对比（completed vs blank）
│   ├── build_groups_from_excel.py# 按 Excel 填充色锚点分组
│   ├── build_data_from_excel.py#   按列映射读数据源
│   ├── build_fill_framework.py #   生成填充计划骨架
│   ├── fill_from_plan.py       #   按 plan 把数据写入模板副本
│   ├── fill_plan/              #   填充计划
│   ├── intermediate/           #   中间产物
│   ├── xlsm/                   #   模板源
│   └── zzz.md                  #   完整流程说明
│
├── nineTools/                  # 独立小工具（不依赖主流水线）
│   ├── id_sorting.py           #   ID 排序（12 位按各位 ASCII 升序）
│   ├── id_sorting_data / id_sorting_result   # 排序输入 / 输出
│   ├── random_id.py            #   随机 16 位 ID 生成（与 assign_ids 同规则）
│   └── random_ids_*.txt        #   生成结果（gitignored）
│
├── y_addreoffici/             # 账号 addreoffici@163.com（按账号分区）
│   └── de_init_template/        # 德国站 Amazon 模板(.xlsm)：coat/dress/pants/shirt/sweatshirt/tracksuit
├── y_yassikzu/               # 账号 yassikzu@yeah.net（按账号分区）
│   ├── de_init_template/        # 德国站 Amazon 模板(.xlsm)：coat/tracksuit
│   └── fr_init_template/        # 法国站 Amazon 模板(.xlsm)：coat/dress/pants/shirt
├── y_addr&yass/               # 多账号共用资源（按国家分区）
│   ├── de_data_pool/            # 德国站数据池：instructions/keywords/key_words_title/finePoints/word_backup/A_Plus_Manager
│   ├── de_feasibility_domain/   # 德国站可行域（dress/top/tractsuit），Master + Slave + needToGenerate
│   ├── fr_data_pool/            # 法国站数据池：instructions/keywords/key_words_title/finePoints&description
│   ├── fr_feasibility_domain/   # 法国站可行域（coat/dress/tops），Master + Slave + needToGenerate
│   └── email.md                 # 邮件相关共用说明
│
├── deprecated/                 # 弃置代码
│   ├── tools/ai_fill.py
│   ├── services/ai_fill.py
│   ├── prompt/                 #   旧版提示词（含邮件/商品描述/女装/男装）
│   ├── ins/                    #   旧版 INS 文案（history_jsutday / lab_ins）
│   └── test_ai.py
│
├── constant/                   # 常量与零散素材（Flirting.md、excel 公式片段；photo/ 等被 gitignore）
├── zip_by_ec/                  # 重构完成后的仓库打包快照（Tools_refactoring_completed.zip，含 .git）
├── logs/                       # 统一日志（同日复用，gitignored）
├── public/                     # 输入（xls_src / xls_xlsx / txt_src，gitignored）
├── outputs/                    # 输出（gitignored）
└── README.md
```

---

## 主流水线：12 步详解

入口 `main.py` → 多文件合并 → `core/runner.py` 按 `steps/__init__.py` 的注册顺序执行 12 个步骤。每步声明 `requires` 依赖，启动时自动校验顺序；失败时默认 fail-fast，可配置 `pipeline_continue_on_error` 跳过继续。

| #  | 步骤               | 文件                          | 作用                                                           |
|----|--------------------|-------------------------------|----------------------------------------------------------------|
| 1  | merge_sheets       | `steps/merge_sheets.py`       | 多 sheet 合并为一张，迁移图片/样式/合并单元格                  |
| 2  | validate           | `steps/validate.py`           | 校验行列数（期望 ~32 列）                                      |
| 3  | insert_columns     | `steps/insert_columns.py`     | 按 `column_insertions` 插入空白列，图片锚点随列平移            |
| 4  | assign_ids         | `steps/assign_ids.py`         | B 列写随机 16 位 ID（`前6位base62 + 6位日期码 + 后4位`）       |
| 5  | cascade_identifier | `steps/cascade_identifier.py` | C 列级联：A 列有色行取 B 列值，否则继承上一行 C                |
| 6  | map_colors         | `steps/map_colors.py`         | J 列按颜色映射表从 I 列查值；未命中记入 `to_be_completed.json` |
| 7  | size_mapping       | `steps/size_mapping.py`       | K 列按尺码映射表原地替换；有色行清空                           |
| 8  | copy_mirror        | `steps/copy_mirror.py`        | 按 `copy_targets`（目标列: 源列）复制列内容                    |
| 9  | mirror_category    | `steps/mirror_category.py`    | AR 列 ← L 列                                                   |
| 10 | calc_price         | `steps/calc_price.py`         | 从 AR 文本提取 JPY 前价格，计算 AS-AV 价格链                   |
| 11 | format_cells       | `steps/format_cells.py`       | 行高、对齐、列宽、E 列 `=LEN(D{行})` 公式                      |
| 12 | finalize           | `steps/finalize.py`           | 输出最终行列数（目标 ~48 列）                                  |

> 扩展新步骤：继承 `core/pipeline.py` 的 `PipelineStep`，实现 `run(ctx)`，在 `steps/__init__.py` 的 `get_steps()` 中注册即可。

---

## Jenkins 全流程

`jenkins.py` 按 `STEPS` 列表顺序逐个调用子脚本，任一失败即中止。**`STEPS` 可自行注释/取消注释**——当前默认只启用 [5/7] 标题优化，其余为注释状态。完整流程如下：

```
[1/7] xls → xlsx              转换源文件（public/xls_src/ → public/xls_xlsx/）
[2/7] Preprocess               去表头 + SKU 去重（preprocess/run.py）
[3/7] Excel pipeline           合并 → 12 步流水线 → 输出（main.py）
[4/7] Color re-processing      颜色尺码大组处理 → 回写第 10 列（color_reprocess.py）
[5/7] Title optimization       提取标题 → DeepSeek 优化 → 回写（title_rewrite.py）★ 默认启用
[6/7] Title auto fill          生成德语标题 → 回写第 4 列（de_title_build.py）
[7/7] Export SKU               导出 SKU 表（export_sku.py）
```

```bash
python jenkins.py
```

---

## 单独运行

```bash
# Excel 流水线
python main.py

# 预处理（去表头 / SKU 去重，原地修改 public/xls_xlsx/）
python preprocess/run.py

# 颜色尺码处理
python tools/color_size_deal/color_reprocess.py

# 标题优化（web 模式，DeepSeek 网页自动化）
python tools/title_optimize/title_rewrite.py

# 热词采集
python tools/needToCollect/hotwords.py

# 服装热词采集+清洗（一条龙：按涨幅降序采集 → 留存原始 raw/ → 清洗 → 留存结果 result/）
#   只保留"穿在身上的衣服"：自动剔除品牌、鞋帽手套配件、颜色/人群等弱属性误报
python tools/needToCollect/fashion_filter/hotwords_fashion.py
#   可选参数：--pages N(拉取页数) --top N --no-clean(只采集) --no-attributes --no-excludes --plain
#   单独清洗（读 raw/ 最新）：python tools/needToCollect/fashion_filter/clean_fashion.py

# 颜色尺码手动处理
python tools/color_size_deal/process.py

# 图片重排（尺码表移到行末）
python tools/image_classification/reorder.py           # 默认逐行扫描
python tools/image_classification/reorder_batch.py      # 批次模式
```
> 注：此前的 `tools/sku_extract`（浏览器自动抓取 SKU）已不在本仓库，相关命令不再可用。

---

## antelope / nineTools 辅助工具

独立小工具，不依赖主流水线，均只读源文件、写新副本。antelope 完整流程见 `antelope/zzz.md`。

### 1) `analysisXlsm.py` — 模板表头 + 可选值 → JSON

只读解析 Amazon 模板 `.xlsm`（如 `y_yassikzu/fr_init_template/coat_template_Eva.xlsm` 的 `Modèle` / `Valeurs valides`），把每个表头的「列号 / 表头名 / 属性键 / 可选值」输出为 JSON，每列还预留 `reserve_flag` / `reserve_mark` 两个标识位。

```bash
python antelope/analysisXlsm.py                               # 默认解析 coat_template_Eva.xlsm
python antelope/analysisXlsm.py 你的模板.xlsm --output out.json   # 指定文件/输出
python antelope/analysisXlsm.py --max-values 5                # 每字段最多列 5 个可选值
python antelope/analysisXlsm.py --show-data                   # 附带每列示例数据
```
默认输出与输入同目录下的 `<模板名>_analysis.json`。

### 2) `fill_from_plan.py` — 按填充计划(plan)把数据写入模板

把你「数据 → 填哪些列、按什么顺序」写成一份 plan JSON，程序据此把数据写入**模板副本**（模板只读）。关键能力：
- **列范围** `col_scope`：只在列出的列填；不在其中的列绝不写。
- **分组** `groups`：`"group_1": "1 & 99"`，父体起始行 & 末子体行；`data_start_row` 统一偏移。
- **每列填充规则**：数据条数=行数→顺序填；=行数-1→只填子体；=0→不填；<阈值→循环铺满；不匹配→`mismatch` 记入报告。

```bash
python antelope/fill_from_plan.py antelope/fill_plan/example_fill_plan.json --report reports.json
```
格式与规则详见 `antelope/zzz.md`，可直接套用的 plan 骨架见 `antelope/fill_plan/fr_shirt_fill_framework.json`。

### 3) `random_id.py` — 随机 16 位 ID

规则与流水线 `steps/assign_ids.py` 完全一致（16 位：前/后段 base62，中间 6 位日期码 digit→letter）。
```bash
python nineTools/random_id.py            # 生成 1 个
python nineTools/random_id.py --count 20 # 生成 20 个
```

---

## 配置 (config.py)

改 `config.py` 即生效，无需改代码。以下为 `config.example.py` 模板默认值，实际以你的 `config.py` 为准。

### 列布局

- `initial_columns` / `final_columns` — 输入 32 列，输出 48 列
- `col_a` ~ `col_av` — 列号常量（col_a=1, col_b=2, col_c=3, col_i=9, col_j=10, col_k=11, col_l=12, col_m=13, col_ar=44, col_as=45, col_at=46, col_au=47, col_av=48）

### 列插入

- `column_insertions` — `[(2,5), (10,1), (14,10)]` 依次在第 2 列前插 5 列、第 10 列前插 1 列、第 14 列前插 10 列

### 镜像复制

- `copy_targets` — `{目标列: 源列}` 映射，如 `{15:26, 16:28, 17:30, 18:32, 19:34, 20:36, 21:38, 22:40, 23:42}`，复制时从 value（源列）写到 key（目标列）

### 随机 ID

- `date_override` — 日期编码（如 `"260814"`，格式 YYMMDD），中间 6 位按 `0→z,1→a,...,9→i` 编码；空则取当天
- `id_factory` — ID 工厂名：`"default_id_factory"`（16 位）/ `"anch_id_factory"`（`Anch` 前缀，20 位）；空则用默认

### 价格计算

- `price_multiplier` — 乘数 `"1.2"`
- `price_subtract` — 减数 `"7.98"`
- `price_add` — 加数 `"6.00"`
- 公式：`AS=base, AT=AS×1.2, AU=AT−7.98, AV=AU+6.00`（base 取自 AR 文本中 JPY 前的价格）

### 格式化

- `row_height` — 行高 `50`
- `cell_h_align` — 水平对齐 `"left"`
- `cell_v_align` — 垂直对齐 `"center"`
- `col_width_1_3` — 第 1-3 列列宽 `17.75`
- `col_width_4` — 第 4 列列宽 `100.0`
- `col_5_formula` — 第 5 列是否写入 `=LEN(D{row})` 公式（默认 `True`）

### I/O

- `src_dir` — 输入目录 `public/xls_xlsx`
- `out_dir` — 输出目录 `outputs`

### 映射表

- `mapping_country` — 映射表国家码，如 `de` / `fr` / `us`，对应 `data/color_mapping_{code}.json`、`data/size_mapping_{code}.json`（模板默认 `fr`）
- `color_mapping_path` → `load_color_mapping()` — 颜色英→德/法映射表
- `size_mapping_path` → `load_size_mapping()` — 尺码映射表

### AI

- `ai_provider` — 模型提供商 `"deepseek"` / `"gemini"`
- `ai_api_key` — API 密钥
- `ai_model` — 模型名（如 `"deepseek-v4-pro"`）
- `gemini_api_key` / `gemini_model` / `gemini_category` — 旧版（已弃用）

### Hotwords

- `hotwords_country` — 目标站点国家码（`--country` 默认值，模板默认 `de`）
- `hotwords_dual_mode` — 双请求开关（`True`=fluctuation+new_rank, `False`=单模式）
- `hotwords_single_mode` — 单请求模式 `"new_rank"` / `"fluctuation"`
- `hotwords_fluc_enabled` — 启用 fluctuation 过滤
- `hotwords_fluc_threshold` — 保留 `fluctuation < -60000` 的词
- `hotwords_rank_enabled` — 启用 new_rank 分档过滤
- `hotwords_rank_threshold_high` — 返回 160-200 条时保留 `new_rank < 200000`
- `hotwords_rank_threshold_mid` — 返回 40-160 条时保留 `new_rank < 200000`

### Pipeline

- `delete_source_after_merge` — 合并后是否删除源文件（默认 `True`）
- `pipeline_continue_on_error` — 单步骤失败后是否继续执行后续步骤（默认 `False`）
- `pipeline_checkpoint_every` — 每 N 步保存检查点（`outputs/.checkpoints/`）；`0` 关闭（默认）

### Retry

- `retry_max_rounds_deepseek` — DeepSeek 网页端重试轮数（默认 `5`）
- `retry_max_rounds_hotwords` — 热词采集重试轮数（默认 `5`）
- `delays` — 网页自动化请求间隔（request_interval / retry_pause / page_ready / upload_processing …）
- `deepseek_selectors` — DeepSeek 网页自动化 CSS 选择器

### Preprocess

- `preprocess_dedup_max_gap` — SKU 去重：同 SKU 有色行最大间距，超此值视为新组（默认 `100`）
- `preprocess_dedup_close_gap` — SKU 去重：两有色锚点行之间夹的行数 ≤ 此值时，删除锚点行及其间所有行（默认 `10`）
- `preprocess_remove_empty_j` — 是否删除 J 列为空的普通数据行（默认 `False`；开启后预处理插入 remove_empty_j 步骤）

### Image Classification

- `img_classify_mode` — 分类引擎 `"ocr"`（默认）/ `"opencv"` / `"heuristic"` / `"all"`（多引擎投票）
- `img_classify_ocr_lang` — OCR 语言包 `"eng+deu"`
- `img_classify_table_min_lines` — OpenCV 模式最少水平线数（默认 `10`，>此值判定为尺码图）
- `img_reorder_mode` — 图片重排模式，三种：
  - `"inline_dual"`（默认）— 原位保留尺码图，后插一份，末尾追加一份；超出列范围从末尾截断
  - `"move_dual"` — 尺码图移除并前移填补，末尾放两份
  - `"copy_single"` — 尺码图复制到行末，原位置标红

---

## AI 模型

`services/ai_client.py` 注册表模式，两者均支持**图片 + 文本**：

- `@AIClient.register("gemini")` — Google Gemini（官方 SDK）
- `@AIClient.register("deepseek")` — DeepSeek（OpenAI 兼容 API，图片走 base64 data URL）

切换只需改 `config.py` 中 `ai_provider`。新增模型：实现 `AIClient` 子类并用 `@AIClient.register("名字")` 注册即可。

---

## 日志

所有模块写入 `logs/{日期}_{8位随机}.log`，同日复用，控制台仅显示关键信息（INFO 级），第三方库日志保持 WARNING 级不刷屏。
