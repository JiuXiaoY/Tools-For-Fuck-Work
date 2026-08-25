# dealExcel_refactoring

> Excel 批量处理流水线 — 32 列 → 48 列，一键从 .xls 到优化输出

---

## 快速开始

```bash
pip install -r requirements.txt

# 创建配置文件（复制模板后填入密钥）
cp config.example.py config.py

# 放入 .xls 到 public/xls_src/，然后：
python jenkins.py
```

输出：`outputs/{日期}v{版本}.xlsx`

---

## 目录

```
dealExcel_refactoring/
│
├── jenkins.py                  # 一键启动全流程
├── main.py                     # Excel 流水线入口
├── config.py                   # 所有配置（config.example.py 是模板）
├── requirements.txt / pyproject.toml
├── REFACTOR_GUIDE.md           # 重构指南
├── ISSUES.md                   # 问题与待办
│
├── constant/                   # 常量（含 photo 目录）
├── zip_by_ec/                  # 按 ec 目录压缩打包
│
├── core/                       # 流水线核心（Pipeline / Step / Context）
├── steps/                      # 12 个流水线步骤
├── preprocess/                 # 预处理（在原始文件上，流水线之前）
│   ├── run.py                  #   入口
│   └── steps/                  #   预处理步骤（去表头 / SKU 去重）
├── services/                   # 工具函数（excel/images/logger/ai_client...）
├── rules/                      # 业务规则（价格提取）
├── data/                       # 映射表
│   ├── color_mapping_de.json   # 颜色 英→德
│   ├── color_mapping_fr.json   # 颜色 英→法
│   ├── size_mapping_de.json    # 尺码映射 (德)
│   ├── size_mapping_fr.json    # 尺码映射 (法)
│   ├── dress_attributes_options_fr.json  # 法站属性可选项知识库（col/neck/...）
│   └── to_be_completed.json    # 待完成项清单
│
├── tools/
│   ├── xls2xlsx.py             # .xls → .xlsx 转换
│   ├── needToCollect/          # 热词采集
│   │   ├── hotwords.py         #   采集程序
│   │   ├── cleaner.py          #   清洗管道
│   │   ├── base_words/         #   基础词库
│   │   ├── result/             #   采集输出
│   │   └── fashion_filter/     #   服装热词采集+清洗（一条龙）
│   │       ├── hotwords_fashion.py    #   主程序：采集 → 留存原始 → 清洗 → 留存结果
│   │       ├── clean_fashion.py       #   清洗逻辑：品类词根/强弱属性/黑名单/品牌移除
│   │       ├── fashion_categories.txt #   服装品类词根（只保留穿在身上的衣服）
│   │       ├── fashion_attributes.txt #   属性词根（! 前缀=强属性可独立保留，否则须搭品类词）
│   │       ├── fashion_excludes.txt   #   黑名单（明确非服装噪声）
│   │       ├── fashion_brands.txt     #   品牌表（token 级移除任意位置的品牌）
│   │       ├── raw/                   #   清洗前原始数据（.gitignored）
│   │       └── result/                #   清洗结果（.gitignored）
│   ├── color_size_deal/        # 颜色尺码处理
│   │   ├── color_reprocess.py  #   Excel → check_.txt → 处理 → 回写
│   │   ├── process.py          #   手动处理 check_.txt
│   │   └── check_.txt
│   ├── title_optimize/         # 标题优化
│   │   ├── title_rewrite.py    #   编排：提取 → 校验 → 优化 → 回写
│   │   ├── deepseek_web.py     #   DeepSeek 网页自动化
│   │   ├── run.py              #   API 模式（暂未使用）
│   │   ├── download.py         #   图片下载
│   │   ├── origin_link / origin_title / optimize_title
│   │   └── temp_photo/
│   ├── title_auto_fill/        # 标题自动填充（TODO）
│   │   ├── de_title_build.py   #   编排器
│   │   ├── de_collect.py       #   采集（空壳）
│   │   ├── de_write_back.py    #   回写第 4 列
│   │   └── final_de_title
│   ├── txt2md.py
│   ├── image_classification/    # 图片分类 & 重排（尺码表检测）
│   │   ├── classify.py          #   三引擎分类器（heuristic / ocr / opencv）
│   │   ├── reorder.py           #   逐行扫描重排
│   │   ├── reorder_batch.py     #   批次重排（按A列有色行分组）
│   │   └── reorder_backup.py    #   旧版备份
│   ├── export_sku/              # SKU 导出
│   │   └── export_sku.py
│   └── write_excel_temp/        # Excel 临时写表
│       ├── write_excel.py
│       └── fill_az_from_help.py
│
├── nineTools/                  # 独立小工具（不依赖主流水线）
│   ├── analysisXlsm.py         #   只读解析 Amazon 模板(.xlsm)：表头 + 该列可选值 → JSON
│   ├── fill_from_plan.py       #   按填充计划(plan)把数据写入模板副本（列范围/分组/循环规则）
│   ├── fill_plan/              #   填充计划模板：example_fill_plan.json + README
│   └── random_id.py            #   随机 16 位 ID 生成（规则与 steps/assign_ids 一致）
│
├── y_addreoffici/             # 账号 addreoffici@163.com（按账号分区）
│   └── de/                      #   └─ 德国站 AI 提示词（原 prompt_de：8 个品类指令 + 关键词库）
│       ├── instructions/
│       └── keywords/
├── y_yassikzu/               # 账号 yassikzu@yeah.net（按账号分区）
│   └── fr/                      #   └─ 法国站 AI 提示词（原 prompt_fr）
│       ├── final_init_template/ # Amazon 模板(.xlsm)：coat/dress/pants/shirt 等
│       ├── instructions/        # 品类指令
│       ├── keywords/            # 关键词库
│       ├── key_words_title/     # 生成的关键词标题（Adam_tops / Adam_pants / Eva_dress）
│       ├── *_feasibility_domain/  # 可行域（dress/tops），Master + Slave + needToGenerate
│       ├── A_Plus_Manager/      # 广告内容管理
│       ├── email_template/      # 邮件模板
│       ├── finePoints&description/  # 卖点与描述
│       └── word_backup/         # 词库备份
│
├── deprecated/                 # 弃置代码（第 4 列 AI 填充）
│   ├── tools/ai_fill.py
│   ├── services/ai_fill.py
│   └── test_ai.py
│
├── logs/                       # 统一日志（同日复用）
├── public/                     # 输入（.gitignored）
├── outputs/                    # 输出（.gitignored）
└── README.md
```

---

## Jenkins 全流程

```bash
python jenkins.py
```

```
[1/7] xls → xlsx              转换源文件
[2/7] Preprocess               去表头 + SKU 去重
[3/7] Excel pipeline           合并 → 12 步流水线 → 输出
[4/7] Color re-processing      颜色尺码大组处理 → 回写第 10 列
[5/7] Title optimization       提取标题 → DeepSeek 优化 → 回写第 8 列
[6/7] Title auto fill          生成德语标题 → 回写第 4 列
[7/7] Export SKU               导出 SKU 表
```

---

## 单独运行

```bash
# Excel 流水线
python main.py

# 颜色尺码处理
python tools/color_size_deal/color_reprocess.py

# 标题优化（web 模式）
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

## nineTools 辅助工具

独立小工具，不依赖主流水线，均只读源文件、写新副本。

### 1) `analysisXlsm.py` — 模板表头 + 可选值 → JSON

只读解析 Amazon 模板 `.xlsm`（如 `y_yassikzu/fr/final_init_template/coat_template_Eva.xlsm` 的 `Modèle` / `Valeurs valides`），把每个表头的「列号 / 表头名 / 属性键 / 可选值」输出为 JSON，每列还预留 `reserve_flag` / `reserve_mark` 两个标识位。

```bash
python nineTools/analysisXlsm.py                               # 默认解析 coat_template_Eva.xlsm
python nineTools/analysisXlsm.py 你的模板.xlsm --output out.json   # 指定文件/输出
python nineTools/analysisXlsm.py --max-values 5                # 每字段最多列 5 个可选值
python nineTools/analysisXlsm.py --show-data                   # 附带每列示例数据
```
默认输出与输入同目录下的 `<模板名>_analysis.json`。

### 2) `fill_from_plan.py` — 按填充计划(plan)把数据写入模板

把你「数据 → 填哪些列、按什么顺序」写成一份 plan JSON，程序据此把数据写入**模板副本**（模板只读）。关键能力：
- **列范围** `col_scope`：只在列出的列填；不在其中的列绝不写。
- **分组** `groups`：`"group_1": "1 & 99"`，父体起始行 & 末子体行；`data_start_row` 统一偏移。
- **每列填充规则**：数据条数=行数→顺序填；=行数-1→只填子体；=0→不填；<阈值→循环铺满；不匹配→`mismatch` 记入报告。

```bash
python nineTools/fill_from_plan.py nineTools/fill_plan/example_fill_plan.json --report reports.json
```
格式与规则详见 `nineTools/fill_plan/README.md`，可直接套用的示例见：
- `nineTools/fill_plan/example_fill_plan.json` — 通用骨架（演示四种规则）
- `nineTools/fill_plan/example_from_givingtree.json` — 从已填好的数据源 `nineTools/TheGivingTree@.xlsm`(DRESS) 抽取前 2 组生成；演示 `cycle`(组内一致列) / `children_only`(父空、只填子体) / `sequential`(逐子变化列) 三种真实场景

### 3) `random_id.py` — 随机 16 位 ID

规则与流水线 `steps/assign_ids.py` 完全一致（16 位：前/后段 base62，中间 6 位日期码 digit→letter）。
```bash
python nineTools/random_id.py            # 生成 1 个
python nineTools/random_id.py --count 20 # 生成 20 个
```

---

## 配置 (config.py)

改值即生效，无需改代码。

### 列布局

- `initial_columns` / `final_columns` — 输入 32 列，输出 48 列
- `col_a` ~ `col_av` — 列号常量（col_a=1, col_b=2, col_c=3, col_i=9, col_j=10, col_k=11, col_l=12, col_m=13, col_ar=44, col_as=45, col_at=46, col_au=47, col_av=48）

### 列插入

- `column_insertions` — `[(2,5), (10,1), (14,10)]` 依次在第 2 列前插 5 列、第 10 列前插 1 列、第 14 列前插 10 列

### 镜像复制

- `copy_targets` — `{源列: 目标列}` 映射，如 `{15:26, 16:28, 17:30, ...}`

### 随机 ID

- `date_override` — 日期编码（`"260731"`），中间 6 位按 `0→z,1→a,...,9→i` 编码；空则取当天

### 价格计算

- `price_multiplier` — 乘数 `"1.2"`
- `price_subtract` — 减数 `"7.98"`
- `price_add` — 加数 `"1.50"`
- 公式：`AS=base, AT=base×1.2, AU=AT−7.98, AV=AU+1.50`

### 格式化

- `row_height` — 行高 `50`
- `cell_h_align` — 水平对齐 `"left"`
- `cell_v_align` — 垂直对齐 `"center"`
- `col_width_1_3` — 第 1-3 列列宽 `17.75`
- `col_width_4` — 第 4 列列宽 `100.0`
- `col_5_formula` — 是否写入 `=LEN(D{row})` 公式

### I/O

- `src_dir` — 输入目录 `public/xls_xlsx`
- `out_dir` — 输出目录 `outputs`

### AI

- `ai_provider` — 模型提供商 `"deepseek"` / `"gemini"`
- `ai_api_key` — API 密钥
- `ai_model` — 模型名 `"deepseek-v4-pro"`
- `gemini_api_key` / `gemini_model` / `gemini_category` — 旧版（已弃用）

### Hotwords

- `hotwords_dual_mode` — 双请求开关（`True`=fluctuation+new_rank, `False`=单模式）
- `hotwords_single_mode` — 单请求模式 `"new_rank"` / `"fluctuation"`
- `hotwords_fluc_enabled` — 启用 fluctuation 过滤
- `hotwords_fluc_threshold` — 保留 `fluctuation < -90000` 的词
- `hotwords_rank_enabled` — 启用 new_rank 分档过滤
- `hotwords_rank_threshold_high` — 160-200 条时保留 `new_rank < 20000`
- `hotwords_rank_threshold_mid` — 40-160 条时保留 `new_rank < 200000`

### Pipeline

- `delete_source_after_merge` — 合并后是否删除源文件（默认 `False`）

### Image Classification

- `img_classify_mode` — 分类引擎 `"ocr"` / `"opencv"` / `"heuristic"` / `"all"`（多引擎投票）
- `img_classify_ocr_lang` — OCR 语言包 `"eng+deu"`
- `img_classify_table_min_lines` — OpenCV 模式最少水平线数（默认 `10`，>此值判定为尺码图）
- `img_reorder_mode` — 图片重排模式，三种：
  - `"inline_dual"`（默认）— 原位保留尺码图，后插一份，末尾追加一份；超出列范围从末尾截断
  - `"move_dual"` — 尺码图移除并前移填补，末尾放两份
  - `"copy_single"` — 尺码图复制到行末，原位置标红

### Retry

- `retry_max_rounds_deepseek` — DeepSeek 网页端重试轮数（默认 `5`）
- `retry_max_rounds_hotwords` — 热词采集重试轮数（默认 `5`）

### Preprocess

- `preprocess_dedup_max_gap` — SKU 去重：同 SKU 有色行最大间距，超此值视为新组（默认 `100`）
- `preprocess_dedup_close_gap` — SKU 去重：两有色锚点行之间夹的行数 ≤ 此值时，删除锚点行及其间所有行（默认 `5`）

### 映射表

- `mapping_country` — 映射表国家码，如 `de` / `fr` / `us`，对应 `data/color_mapping_{code}.json`、`data/size_mapping_{code}.json`（默认 `de`）
- `color_mapping_path` → `load_color_mapping()` — 颜色英→德（`data/color_mapping_{mapping_country}.json`，742 条）
- `size_mapping_path` → `load_size_mapping()` — 尺码映射（`data/size_mapping_{mapping_country}.json`）

---

## AI 模型

`services/ai_client.py` 注册表模式：

- `@AIClient.register("gemini")` — 支持图片
- `@AIClient.register("deepseek")` — 纯文本（API 不支持图片）

切换只需改 `config.py` 中 `ai_provider`。

---

## 日志

所有模块写入 `logs/{日期}_{8位随机}.log`，同日复用，控制台仅显示关键信息。

---