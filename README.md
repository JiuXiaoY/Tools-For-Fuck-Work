# dealExcel_refactoring

Excel 批处理与 Amazon 模板填充工具集。仓库包含两条主要流程：

- 根目录流水线：整理普通 `.xlsx` 数据，执行合并、列转换、映射、价格计算和格式化。
- `antelope/`：将数据源写入 Amazon `.xlsm` 模板副本。

独立工具集中在 `tools/` 和 `nineTools/`。提示词、关键词、映射表和模板属于业务资源，不是程序说明文档。

## 使用前注意

1. `config.py` 是本地配置，已被 Git 忽略。密钥不得写入 `config.example.py`、Markdown、日志或压缩包。
2. `tools/xls2xlsx.py` 当前只修改文件扩展名，不会把真实的旧版 `.xls` 转换成 `.xlsx`。建议直接把有效 `.xlsx` 放入 `public/xls_xlsx/`。
3. `delete_source_after_merge=True` 会在主流水线处理完成前删除源文件。重要输入应先备份，正式使用前建议关闭该选项。
4. `zip_dir.py` 当前没有敏感文件排除规则，不应直接用于打包本仓库、浏览器目录或本地配置。

当前技术风险和待办见 [ISSUES.md](ISSUES.md)。

## 环境

- Python 3.10+
- Windows 为主要运行环境
- 核心依赖：`openpyxl`、`Pillow`、`requests`
- 部分 AI、浏览器和图像工具还需要 Playwright、Google GenAI、OpenAI、NumPy、OpenCV 等可选依赖

安装基础依赖：

```bash
python -m pip install -r requirements.txt
```

创建本地配置：

```powershell
Copy-Item config.example.py config.py
```

复制后应检查并清空示例中的任何凭据，再填写自己的本地配置。

## 根目录流水线

推荐把有效 `.xlsx` 文件放入：

```text
public/xls_xlsx/
```

运行当前默认全流程：

```bash
python jenkins.py
```

`jenkins.py` 当前启用四个步骤：

1. `tools/xls2xlsx.py`
2. `preprocess/run.py`
3. `main.py`
4. `tools/color_size_deal/color_reprocess.py`

如果输入本来就是 `.xlsx`，应跳过第一步，直接运行：

```bash
python preprocess/run.py
python main.py
python tools/color_size_deal/color_reprocess.py
```

最终文件写入：

```text
outputs/{月}.{日}v{版本}_{国家}.xlsx
```

### 主流水线步骤

`main.py` 注册 12 个步骤：

| 顺序 | 步骤 | 作用 |
|---:|---|---|
| 1 | `merge_sheets` | 合并工作簿内的多个工作表 |
| 2 | `validate` | 记录处理前行列数；目前不会阻止异常输入 |
| 3 | `insert_columns` | 根据配置插入列并调整图片锚点 |
| 4 | `assign_ids` | 写入随机 ID |
| 5 | `cascade_identifier` | 按父体行级联标识 |
| 6 | `map_colors` | 应用颜色映射 |
| 7 | `size_mapping` | 应用尺码映射 |
| 8 | `copy_mirror` | 按配置复制镜像列 |
| 9 | `mirror_category` | 复制价格/类目来源列 |
| 10 | `calc_price` | 计算价格链 |
| 11 | `format_cells` | 设置行高、列宽、对齐和公式 |
| 12 | `finalize` | 记录最终行列数；目前不会阻止异常输出 |

步骤顺序和依赖在 `steps/__init__.py` 与各步骤的 `requires` 中声明。

## antelope 模板填充

完整说明见 [antelope/zzz.md](antelope/zzz.md)。

基本入口：

```bash
python antelope/run_all.py
```

每个批次运行前，先检查 `antelope/zconfig.constant.py` 顶部的：

- `ACTIVE_CATEGORY`
- `DATA_SOURCE_A`
- `TEMPLATE_B`
- `TEMPLATE_C`
- `TEMPLATE_OUTPUT`

模板和数据源位于 `antelope/xlsm/`，该目录不进入 Git。最终结果写入根目录 `outputs/`。

## 目录职责

| 路径 | 内容 |
|---|---|
| `core/` | PipelineContext、PipelineStep 和调度器 |
| `steps/` | 根目录主流水线步骤 |
| `preprocess/` | 主流水线前的源文件预处理 |
| `services/` | Excel、图片、日志、映射记录和 AI 客户端 |
| `rules/` | 业务规则 |
| `data/` | 颜色、尺码等固定映射数据 |
| `tools/` | 与主流程相关的辅助工具 |
| `antelope/` | Amazon 模板填充流程 |
| `nineTools/` | 相互独立的小工具，说明见 [nineTools/zzz.md](nineTools/zzz.md) |
| `y_addr&yass/` | 多账号共用业务素材和提示词 |
| `y_addreoffici/`、`y_yassikzu/` | 账号模板资源 |
| `deprecated/` | 已弃用代码与历史提示词，仅供追溯 |
| `public/` | 本地输入目录，不进入 Git |
| `outputs/` | 本地输出目录，不进入 Git |
| `logs/` | 运行日志，不进入 Git |

## 相关子目录说明

- [antelope/zzz.md](antelope/zzz.md)：Amazon 模板填充流程
- [antelope/values/zzz.md](antelope/values/zzz.md)：多行值文件规则
- [nineTools/zzz.md](nineTools/zzz.md)：独立工具索引
- [tools/needToCollect/base_words/zzz.md](tools/needToCollect/base_words/zzz.md)：基础词库规则
- [tools/needToCollect/fashion_filter/zzz.md](tools/needToCollect/fashion_filter/zzz.md)：服装热词采集与清洗

## Markdown 命名约定

- 仓库根目录只有本文件使用 `README.md`。
- 根目录其他 Markdown 按功能命名，例如 `ISSUES.md`。
- 子目录中的通用说明、目录索引或占位文档统一命名为 `zzz.md`。
- 提示词、关键词、商品描述、输入清单和生成结果属于业务数据，应继续使用能表达业务用途的文件名。

## 开发约定

- 不在源码或文档中保存凭据。
- 不提交日志、浏览器用户目录、批次中间产物和输出文件。
- 修改 Excel 处理逻辑时，至少验证行列数、公式、合并单元格和图片锚点。
- 新增步骤时声明唯一 `name` 和真实的 `requires`。
- 更新行为后同步修改对应的 `zzz.md` 或根目录 `README.md`，避免维护完整且容易失真的目录树。
