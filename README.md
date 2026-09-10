# dealExcel_refactoring

> Excel 批量处理流水线 — 32 列 → **49 列**，一键从 .xls 到优化输出

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

输出：**`outputs/{月}.{日}v{版本}_{国家}.xlsx`**（如 `9.2v1_de.xlsx`；同日多次运行自动递增 v2、v3…，国家码取 `config.mapping_country`）

> 下游工具统一用 `config.resolve_output_xlsx(out_dir, date_str, mapping_country)` 定位该文件：取同日同国家下**版本号最大**的一个；若只有旧命名（无国家后缀）则回退兼容，都没有时返回 v1 路径。

---

## 目录结构

```
dealExcel_refactoring/
│
├── jenkins.py                  # 一键启动全流程（STEPS 列表可编辑，见下文）
├── main.py                     # Excel 流水线入口（多文件合并 + 12 步流水线）
├── config.py                   # 所有配置（config.example.py 是模板；config.py 不入库）
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
│   ├── insert_columns.py       #   ③ 按配置插入 17 个空白列（32→49，图片锚点同步平移）
│   ├── assign_ids.py           #   ④ B 列随机 16 位 ID（中间 6 位日期码；ID 工厂可配）
│   ├── cascade_identifier.py   #   ⑤ C 列级联填充（按 A 列填充色取 B 列，否则继承上一行）
│   ├── map_colors.py           #   ⑥ K 列颜色映射（源 J 列；未命中记入 data/to_be_completed.json）
│   ├── size_mapping.py         #   ⑦ L 列尺码映射（原地替换，有色行清空）
│   ├── copy_mirror.py          #   ⑧ 按 copy_targets 源列→目标列镜像复制（图片列）
│   ├── mirror_category.py      #   ⑨ AS 列 ← M 列
│   ├── calc_price.py           #   ⑩ AT-AW 价格链计算（JPY 锚定提取基数）
│   ├── format_cells.py         #   ⑪ 行高 / 对齐 / 列宽 / F 列 =LEN(D) 公式
│   ├── finalize.py             #   ⑫ 输出最终行列数
│   └── remove_header.py        #   （旧版未注册，仅存档；去表头请用 preprocess/）
│
├── preprocess/                 # 预处理（在 public/xls_xlsx/ 原始文件上原地修改，流水线之前）
│   ├── run.py                  #   入口
│   └── steps/
│       ├── remove_header.py    #     去表头（A1 无填充色则删除首行）
│       ├── remove_empty_j.py   #     移除 J 列空的无色行（config 开关控制；作用于源文件）
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
├── data/                       # 映射表（固定文件）
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
│   ├── color_size_deal/        # 颜色尺码处理（列位已随 49 列布局更新）
│   │   ├── color_reprocess.py  #   Excel → check_.txt → process.py 处理 → 回写 K 列(11)
│   │   ├── process.py          #   手动处理 check_.txt（组内重复前缀编号 + 去尺码列）
│   │   └── check_.txt          #   中间产物（gitignored）
│   ├── title_optimize/         # 标题优化（DeepSeek 网页自动化为主）
│   │   ├── title_rewrite.py    #   编排：提取(I→origin_title, P→origin_link) → 校验 → 优化 → 回写
│   │   ├── deepseek_web.py     #   DeepSeek 网页自动化（playwright，登录态保存复用）
│   │   ├── run.py              #   API 模式（图片 + 原标题 → AI 优化，可切 gemini/deepseek）
│   │   ├── download.py         #   图片下载
│   │   ├── origin_link / origin_title / optimize_title   # 中间产物（gitignored）
│   │   └── temp_photo / browser_data / deepseek_state.json # 临时图/浏览器数据（gitignored）
│   ├── title_auto_fill/        # 标题自动填充（德语）
│   │   ├── de_title_build.py   #   编排器：collect → write back
│   │   ├── de_collect.py       #   采集（当前为占位，未实现）
│   │   ├── de_write_back.py    #   回写第 4 列(D) + 空值填上一行公式
│   │   ├── gemini_web.py       #   Gemini 网页登录会话（playwright）
│   │   └── final_de_title / final_de_title_s  # 中间产物（gitignored）
│   ├── image_classification/   # 图片分类 & 重排（尺码表检测）
│   │   ├── classify.py         #   三引擎分类器（heuristic / ocr / opencv，可多引擎投票）
│   │   ├── reorder.py          #   逐行扫描重排（P-X 列 16-24，多线程）
│   │   ├── reorder_batch.py    #   批次重排（按 A 列有色行分组）
│   │   ├── reorder_backup.py   #   旧版备份
│   │   └── images_awaiting/    #   待处理图片（gitignored）
│   ├── export_sku/             # SKU 导出（前两列 → outputs/{日期} - N.xlsx）
│   │   └── export_sku.py
│   └── write_excel_temp/       # Excel 临时写表
│       ├── write_excel.py      #   生成示例 .xlsx
│       └── fill_az_from_help.py#   按 A 列有色分区循环写 AZ 列(52)；默认源自动取当日输出
│
├── antelope/                  # 填充计划生成工具（只读源、写新副本）
│   ├── zconfig.constant.py     #   路径与配置唯一真源（ACTIVE_CATEGORY / 列映射 / 输出名）
│   ├── common.py               #   公共工具 + 统一日志 setup_log()
│   ├── analysisXlsm.py         #   模板表头 + 可选值 → JSON（模板层）
│   ├── column_diff.py          #   列差异对比（completed vs blank，模板层）
│   ├── build_groups_from_excel.py# 按 Excel 填充色锚点分组（数据层）
│   ├── build_data_from_excel.py#   按 col_mapping 读数据源（数据层）
│   ├── build_m_data.py         #   M 占位数据生成（数据层）
│   ├── ai_pick_attributes.py   #   AI 分批网页选值（数据层；groups 指纹门禁）
│   ├── build_fill_framework.py #   生成填充计划骨架（plan）
│   ├── fill_from_plan.py       #   按 plan 把数据写入模板副本
│   ├── run_all.py              #   全流程一键运行（①~⑨，注释式断点续跑）
│   ├── intermediate/           #   数据层中间产物（每次数据批次重跑）
│   ├── intermediate_tpl/       #   模板层中间产物（只需跑一次）+ 人工固定文件
│   ├── fill_plan/              #   填充计划
│   ├── log/                    #   运行日志（{日期}_atl_{用户}.log）
│   ├── xlsm/                   #   模板源与数据源（gitignored，换批次频繁、体积大）
│   └── zzz.md                  #   完整流程说明
│
├── nineTools/                  # 独立小工具（按用途分子目录，详见 nineTools/README.md）
│   ├── README.md               #   工具索引
│   ├── color_size_change/      #   C&S_change.py + color_change / size_change（德→法映射转换）
│   ├── id_sorting/             #   id_sorting.py + id_sorting_data / id_sorting_result
│   ├── random_id/              #   random_id.py（+ random_ids_*.txt，gitignored）
│   ├── sku_extract/            #   extract_sku.py（从抓取文本抽 SKU，去重）
│   └── zip/                    #   zip_dir.py（压缩目录 → zip_by_ec/{日期}_{用户}.zip）
│
├── y_addreoffici/             # 账号 addreoffici@163.com（按账号分区）
│   └── de_init_template/        # 德国站 Amazon 模板(.xlsm)
├── y_yassikzu/               # 账号 yassikzu@yeah.net（按账号分区）
│   ├── de_init_template/        # 德国站 Amazon 模板(.xlsm)
│   └── fr_init_template/        # 法国站 Amazon 模板(.xlsm)
├── y_addr&yass/               # 多账号共用资源（按国家分区）
│   ├── 提示词优化.md            # 标题生成提示词「标准模板」（各分类 ins 文件以此为基准）
│   ├── de_data_pool/            # 德国站数据池：instructions/keywords/key_words_title/finePoints…
│   ├── de_feasibility_domain/   # 德国站可行域（dress/pants/top/tractsuit），Master + Slave + needToGenerate
│   ├── fr_data_pool/            # 法国站数据池：instructions/keywords/key_words_title/finePoints&description
│   ├── fr_feasibility_domain/   # 法国站可行域（coat/dress/pants/tops），Master + Slave + needToGenerate
│   └── email.md                 # 邮件相关共用说明
│
├── deprecated/                 # 弃置代码（tools/、services/、prompt/、ins/、test_ai.py）
├── constant/                   # 常量与零散素材（Flirting.md、excel 公式片段；photo/ 等被 gitignore）
├── zip_by_ec/                  # 仓库/目录打包快照（含 {日期}_{用户}.zip，由 nineTools/zip 生成）
├── logs/                       # 统一日志（同日复用，gitignored）
├── public/                     # 输入（xls_src / xls_xlsx / txt_src，gitignored）
├── outputs/                    # 输出（gitignored）
└── README.md
```

---

## 主流水线：12 步详解

入口 `main.py` → 取 `public/xls_xlsx/*.xlsx`（1 个则直接复制，多个则合并）→ 生成 `outputs/{月}.{日}v{n}_{国家}.xlsx` → 对该文件跑 12 步流水线并**原地保存**。每步声明 `requires` 依赖，启动时自动校验顺序；失败默认 fail-fast，可配 `pipeline_continue_on_error` 继续。

| #  | 步骤               | 文件                          | 作用                                                           |
|----|--------------------|-------------------------------|----------------------------------------------------------------|
| 1  | merge_sheets       | `steps/merge_sheets.py`       | 多 sheet 合并为一张，迁移图片/样式/合并单元格                  |
| 2  | validate           | `steps/validate.py`           | 校验行列数（期望 ~32 列）                                      |
| 3  | insert_columns     | `steps/insert_columns.py`     | 按 `column_insertions` 插入 17 列 → **49 列**；图片锚点随列平移 |
| 4  | assign_ids         | `steps/assign_ids.py`         | B 列写随机 16 位 ID（`前6位base62 + 6位日期码 + 后4位`）       |
| 5  | cascade_identifier | `steps/cascade_identifier.py` | C 列级联：A 列有色行取 B 列值，否则继承上一行 C                |
| 6  | map_colors         | `steps/map_colors.py`         | K(11) 列按颜色映射表从 J(10) 列查值；未命中记入 `to_be_completed.json` |
| 7  | size_mapping       | `steps/size_mapping.py`       | L(12) 列按尺码映射表原地替换；有色行清空                       |
| 8  | copy_mirror        | `steps/copy_mirror.py`        | 按 `copy_targets`（目标列: 源列）复制图片列（16↔27 … 24↔43）   |
| 9  | mirror_category    | `steps/mirror_category.py`    | AS(45) 列 ← M(13) 列                                           |
| 10 | calc_price         | `steps/calc_price.py`         | 从 AS 文本提取 JPY 前价格，计算 AT-AW(46-49) 价格链            |
| 11 | format_cells       | `steps/format_cells.py`       | 行高、对齐、列宽、**F(6) 列 `=LEN(D{行})`** 公式               |
| 12 | finalize           | `steps/finalize.py`           | 输出最终行列数（目标 49 列）                                   |

> 扩展新步骤：继承 `core/pipeline.py` 的 `PipelineStep`，实现 `run(ctx)`，在 `steps/__init__.py` 的 `get_steps()` 中注册即可。

### 49 列布局关键列位

| 列 | 索引 | 说明 |
|----|------|------|
| A  | 1  | 系统 SKU / 分组锚点（A 列有色行 = 父体） |
| B  | 2  | 随机 ID（`Anch` + 16 位） |
| C  | 3  | 级联 ID（同组继承） |
| D  | 4  | 标题列（宽度 100；由标题类工具写入） |
| **E** | **5** | **新增空列（D 之后多出的一列）** |
| F  | 6  | 长度公式列：`=LEN(D{行})` |
| G  | 7  | 空 |
| J  | 10 | 原始颜色（英） |
| K  | 11 | 映射后颜色（德/法）→ `color_reprocess` 处理列 |
| L  | 12 | 映射后尺码 |
| M  | 13 | 价格/类目文本（`mirror_category` 源列） |
| P–X | 16–24 | 图片链接目标列（`copy_mirror` 写入；`image_classification` 处理范围） |
| AA–AQ | 27–43 | 原始图片链接列（镜像源） |
| AS | 45 | ← M(13) 镜像 |
| AT–AW | 46–49 | 价格链（`calc_price`） |

> 注：源文件第 2/3 列落在 H/I(8/9)，源第 4/5/6 列落在 J/K/L(10/11/12)；除 D 后新增一列外，**所有原始列相对关系不变、统一右移一位**。

---

## Jenkins 全流程

`jenkins.py` 按 `STEPS` 列表顺序逐个调用子脚本，任一失败即中止。**`STEPS` 可自行注释/取消注释**——当前默认只启用前 4 步，其余为注释状态。完整流程如下：

```
[1/7] xls → xlsx              转换源文件（public/xls_src/ → public/xls_xlsx/）
[2/7] Preprocess               去表头 + SKU 去重（preprocess/run.py）
[3/7] Excel pipeline           合并 → 12 步流水线 → outputs/{月}.{日}v{n}_{国家}.xlsx（main.py）
[4/7] Color re-processing      颜色尺码大组处理 → 回写 K 列(11)（color_reprocess.py）★ 默认启用
[5/7] Title optimization       提取标题 → DeepSeek 优化 → 回写 I 列(9)（title_rewrite.py）
[6/7] Title auto fill          生成德语标题 → 回写第 4 列(D)（de_title_build.py）
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
python tools/needToCollect/fashion_filter/hotwords_fashion.py
#   可选参数：--pages N(拉取页数) --top N --no-clean(只采集) --no-attributes --no-excludes --plain
#   单独清洗（读 raw/ 最新）：python tools/needToCollect/fashion_filter/clean_fashion.py

# 颜色尺码手动处理
python tools/color_size_deal/process.py

# 图片重排（尺码表移到行末）
python tools/image_classification/reorder.py           # 默认逐行扫描
python tools/image_classification/reorder_batch.py      # 批次模式
```

> 注：`tools/sku_extract`（浏览器自动抓取 SKU）已不在本仓库；等价功能见 `nineTools/sku_extract/extract_sku.py`（从抓取文本抽 SKU）。

---

## antelope —— 填充计划生成（独立于主流水线）

### 批次标识：三段式 ACTIVE_CATEGORY

`zconfig.constant.py` 的 `ACTIVE_CATEGORY = "{限定词}_{国家}_{类型}"`（如 `addr_fr_tops`）决定：模板集、中间产物命名、最终输出名。**三段中任一部分不同 = 三件套（base/complete/输出模板）不同**，模板层产物需重新生成。国家段决定模板工作表名（fr：`Modèle`/`Valeurs valides`；de：`Vorlage`/`Gültige Werte`）。

### 中间产物分两层

| 层 | 目录 | 内容 | 何时跑 |
|---|---|---|---|
| 模板层（只跑一次） | `intermediate_tpl/<类别>/` | `blank / completed / column_diff` + 人工维护的 `col_mapping` | 只依赖 base/complete；三件套不变则复用 |
| 共享手动配置 | `intermediate_tpl/mode_customise.json` | 列填充模式，按 `ACTIVE_CATEGORY` 标签分段（如 `{"17": "cycle"}`） | 人工维护，可缺省 |
| 数据层（每批重跑） | `intermediate/<类别>/` | `groups / data / ai_prompt/` + `.xlsx_dataSource_m.json` | 依赖数据源 A，数据一变就重跑 |

### 步骤与运行

| 步 | 脚本 | 产物 |
|---|---|---|
| ① | `analysisXlsm.py`（base） | `blank.json` |
| ② | `analysisXlsm.py`（complete） | `completed.json` |
| ③ | `column_diff.py` | `column_diff.json`（C−B 待填列 = col_scope） |
| ④ | `build_groups_from_excel.py` | `groups.json`（A 列有色锚点分组） |
| ⑤ | `build_data_from_excel.py` | `data.json`（按 `col_mapping` 取数） |
| ⑥ | `build_m_data.py` | `.xlsx_dataSource_m.json`（占位 `dataTemp`） |
| ⑦ | `ai_pick_attributes.py` | 更新 M（AI 分批选值） |
| ⑧ | `build_fill_framework.py` | `fill_plan/<类别>_fill_framework.json`（plan） |
| ⑨ | `fill_from_plan.py` | `outputs/<类别>_filled.xlsm` |

`run_all.py`：main 内每步一行代码，**注释掉前面已完成的步骤即从剩余步骤连续跑完**（连续后缀，不支持跳步）；①②③ 为模板层，产物比模板文件新时**自动跳过**。

### AI 选值（⑦）要点

- **分批询问**：默认每批 10 条产品（`--batch-size` 可调，0=全部一批），每批一个 `attributes_batchNN.txt` 提示词与 `attributes_batchNN_result.txt` 回答；回答文件存在则复用、跳过网页。
- **groups.json 指纹门禁**：每次运行对 `groups.json` 取 SHA-256 记入 `ai_prompt/groups_fingerprint.txt`。
  - 指纹**一致** → 所有批次复用已有回答（个别缺回答的批次再询问）；
  - 指纹**变了/无记录** → 删除全部旧回答，**所有批次重新询问**（避免跨数据批次误用旧答案）。
- 校验：结束时会检查「有可选值的列是否残留占位（`dataTemp`）」，并列出未识别块头/零值列，便于定位回答问题。

### 日志

所有 antelope 脚本的输出统一写入 **`antelope/log/{当天日期}_atl_{操作用户}.log`**（追加、UTF-8、自动清洗 NBSP），**控制台不再打印**；`run_all` 与其子进程写同一文件，每次运行有分隔头。

> `antelope/xlsm/`（模板与数据源）、`antelope/intermediate/*/ai_prompt/`、`antelope/web_data/`、`.deepseek_state.json` 均已加入 `.gitignore`，不入库。

---

## nineTools —— 独立小工具（按用途分子目录）

索引见 **`nineTools/README.md`**：

| 目录 | 工具 | 用途 |
|---|---|---|
| `color_size_change/` | `C&S_change.py` | 颜色/尺寸映射转换：德 → 原始 → 法（映射表在 `data/`；直接覆盖同目录 `color_change` / `size_change`） |
| `id_sorting/` | `id_sorting.py` | 12 位 ID 按每位 ASCII 值升序排序（`id_sorting_data` → `id_sorting_result`） |
| `random_id/` | `random_id.py` | 随机 16 位 ID（规则同 `steps/assign_ids.py`；>100 条自动落盘 `random_ids_*.txt`，gitignored） |
| `sku_extract/` | `extract_sku.py` | 从抓取文本（`SKU3`）抽取「SKU」标记后的值、去重输出 |
| `zip/` | `zip_dir.py` | 压缩目录（默认 `besskyproject/Means_of_production`）→ `zip_by_ec/{当天日期}_{操作用户}.zip` |

```bash
python nineTools/color_size_change/C&S_change.py
python nineTools/id_sorting/id_sorting.py
python nineTools/random_id/random_id.py
python nineTools/sku_extract/extract_sku.py
python nineTools/zip/zip_dir.py            # 可选：--force / --level N / 指定源目录与输出
```

---

## y_addr&yass —— 标题提示词与可行域

- **标准模板**：`y_addr&yass/提示词优化.md` —— 各分类提示词文件（`{de,fr}_data_pool/instructions/new_ins/*_ins_Anq.md`）以其规则为基准，仅「用词」与「路径」按国家/品类/性别不同。
- **数据池 / 可行域**：提示词中的输入、词库与产出路径分别指向 `{de,fr}_data_pool/keywords/…`、`{de,fr}_feasibility_domain/<类别>/{needToGenerate,Master,Slave}`。

---

## 配置 (config.py)

改 `config.py` 即生效（该文件不入库，模板为 `config.example.py`）。

### 列布局（32 → 49 列）

- `initial_columns = 32`、`final_columns = 49`
- 列常量：`col_a=1, col_b=2, col_c=3, col_i=10, col_j=11, col_k=12, col_l=13, col_m=14, col_ar=45, col_as=46, col_at=47, col_au=48, col_av=49, col_len=6`
- `col_len` = 长度公式列 **F**（写入 `=LEN(D{行})`，D 为标题列，位置不变）

### 列插入

- `column_insertions = [(2,6), (11,1), (15,10)]` — 依次在第 2 列前插 6 列、第 11 列前插 1 列、第 15 列前插 10 列；合计 17 列 → 32+17 = **49**
- 说明：前导空列由 5 变 6（D 之后多留一列 E），后两个插入点随之顺延 +1，保证**所有原始列相对关系不变、统一右移一位**

### 镜像复制

- `copy_targets` — `{目标列: 源列}`，如 `{16:27, 17:29, 18:31, 19:33, 20:35, 21:37, 22:39, 23:41, 24:43}`；复制时从 value（源列）写到 key（目标列）

### 随机 ID

- `date_override` — 日期编码（如 `"260902"`，格式 YYMMDD），中间 6 位按 `0→z,1→a,...,9→i` 编码；空则取当天
- `id_factory` — ID 工厂名：`"default_id_factory"`（16 位）/ `"anch_id_factory"`（`Anch` 前缀，20 位）；空则用默认

### 价格计算

- `price_multiplier` / `price_subtract` / `price_add` — `1.2` / `7.98` / `6.00`
- 公式：`AT=base, AU=AT×1.2, AV=AU−7.98, AW=AV+6.00`（base 取自 AS 文本中 JPY 前的价格）

### 格式化

- `row_height=50`、`cell_h_align="left"`、`cell_v_align="center"`
- `col_width_1_3=17.75`（第 1-3 列）、`col_width_4=100.0`（第 4 列标题）
- `col_5_formula=True` — 是否写长度公式（写到 `col_len` 列 F）

### I/O 与输出命名

- `src_dir="public/xls_xlsx"`、`out_dir="outputs"`
- 输出文件：`outputs/{月}.{日}v{版本}_{mapping_country}.xlsx`；下游用 `config.resolve_output_xlsx()` 定位（同日同国家取最大版本，兼容无国家后缀的旧命名）

### 映射表

- `mapping_country` — `de` / `fr` / `us` …，对应 `data/color_mapping_{code}.json`、`data/size_mapping_{code}.json`
- `color_mapping_path` → `load_color_mapping()`；`size_mapping_path` → `load_size_mapping()`

### AI

- `ai_provider` — `"deepseek"` / `"gemini"`；`ai_api_key`；`ai_model`（如 `"deepseek-v4-pro"`）
- `gemini_*` 为旧版（已弃用）

### Hotwords

- `hotwords_country`、`hotwords_dual_mode`、`hotwords_single_mode`、`hotwords_fluc_enabled` / `hotwords_fluc_threshold`、`hotwords_rank_enabled` / `hotwords_rank_threshold_high` / `hotwords_rank_threshold_mid`

### Pipeline

- `delete_source_after_merge`（默认 `True`）、`pipeline_continue_on_error`（默认 `False`）、`pipeline_checkpoint_every`（`0` 关闭；>0 时每 N 步存 `outputs/.checkpoints/`）

### Retry / Preprocess / Image Classification

- `retry_max_rounds_deepseek`、`retry_max_rounds_hotwords`、`delays`、`deepseek_selectors`
- `preprocess_dedup_max_gap`、`preprocess_dedup_close_gap`、`preprocess_remove_empty_j`
- `img_classify_mode`(`ocr`/`opencv`/`heuristic`/`all`)、`img_classify_ocr_lang`、`img_classify_table_min_lines`
- `img_reorder_mode`：`inline_dual`（默认）/ `move_dual` / `copy_single`

---

## AI 模型

`services/ai_client.py` 注册表模式，两者均支持**图片 + 文本**：

- `@AIClient.register("gemini")` — Google Gemini（官方 SDK）
- `@AIClient.register("deepseek")` — DeepSeek（OpenAI 兼容 API，图片走 base64 data URL）

切换只需改 `config.py` 中 `ai_provider`。新增模型：实现 `AIClient` 子类并用 `@AIClient.register("名字")` 注册即可。

---

## 日志

- **主流水线/工具**：`logs/{日期}_{8位随机}.log`，同日复用；控制台仅显示关键信息（INFO 级），第三方库保持 WARNING 级。
- **antelope**：`antelope/log/{当天日期}_atl_{操作用户}.log`（追加；含每次运行的时间与命令分隔头；控制台不打印）。

---

## 版本变动速览（近期）

- 列布局 **48 → 49**：D 之后新增一列（E 空），长度公式由 E 改为 **F**，其余列整体右移一位；`config.py` / `config.example.py` 的列常量、`column_insertions`、`copy_targets` 同步更新。
- 下游工具列号同步：`color_reprocess` → K/L(11/12)；`title_rewrite` → I(9)/P(16)；`image_classification` → P–X(16–24)。
- 输出文件命名加入国家后缀，并新增 `resolve_output_xlsx()` 统一定位（取最大版本，兼容旧命名）。
- `antelope`：三段式 `ACTIVE_CATEGORY`、模板层/数据层产物分离、模板步骤自动跳过、AI 分批询问 + groups 指纹门禁、统一文件日志。
- `nineTools`：按用途分子目录（含 `README.md`）。
- `.gitignore`：新增 `antelope/xlsm/`、`nineTools/**/*.txt` 等。
