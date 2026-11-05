# 亚马逊德法站搜索建议采集

通过亚马逊公开建议接口采集德法站搜索建议，只依赖 Python 3.10 及以上版本的标准库。

## 输入和配置

- `keywords_de.txt`：德国关键词，每行一个词或词组。
- `keywords_fr.txt`：法国关键词，每行一个词或词组。
- `config.py`：所有默认配置，修改其中的 `SETTINGS` 字典即可。

词表保存为 UTF-8，支持 BOM。空行忽略，重复输入自动合并。输入词只用于查询，结果词表保留亚马逊实际返回的原文。

| 配置 | 默认值 | 含义 |
| --- | --- | --- |
| `markets` | `["de", "fr"]` | 采集站点，可只保留一站 |
| `category` | `"aps"` | 搜索类别，`aps` 为全部类别 |
| `expand` | `"none"` | `none` 原词；`letters` 字母扩展；`letters-digits` 字母及数字扩展 |
| `interval` | `1.2` | 请求间隔秒数，不得小于 0.5 |
| `timeout` | `15` | 单次请求超时秒数 |
| `retries` | `2` | 失败后的额外重试次数，范围 0 到 5 |
| `cache_hours` | `24` | 缓存有效小时数，0 表示每次重新采集 |

## 运行

在项目根目录执行：

```powershell
python nineTools/getSugWord/get_sug_word.py
```

默认采集两个站点，只查询输入词本身。首次运行前填写相应站点的词表；词表为空时程序提示并停止。

```powershell
# 只采集德国或法国
python nineTools/getSugWord/get_sug_word.py --market de
python nineTools/getSugWord/get_sug_word.py --market fr

# 按字母扩展查询
python nineTools/getSugWord/get_sug_word.py --expand letters

# 按字母和数字扩展查询
python nineTools/getSugWord/get_sug_word.py --expand letters-digits

# 每次最多处理 5 个未缓存前缀，再次运行可继续
python nineTools/getSugWord/get_sug_word.py --expand letters --max-queries 5

# 使用另一份词表，须指定单个站点
python nineTools/getSugWord/get_sug_word.py --market de --input nineTools/getSugWord/keywords_de.txt

# 只看计划，不联网、不写输出
python nineTools/getSugWord/get_sug_word.py --dry-run

# 忽略缓存，重新采集
python nineTools/getSugWord/get_sug_word.py --refresh
```

`letters` 对每个输入词生成最多 28 个前缀：原词、原词后加空格、原词后加空格和 a 到 z。`letters-digits` 额外增加 0 到 9，共最多 38 个前缀。查询前缀不会被自行当作建议词写入结果。

`--input` 只接受 `.txt`，相对路径以命令运行目录为准。`--config` 可指定另一份包含 `SETTINGS` 字典的 `.py` 配置，命令行参数覆盖配置中的同名选项。

## 输出格式

每次运行创建独立的 `outputs/时间戳/` 目录，保留之前的结果。

| 文件 | 内容 |
| --- | --- |
| `de_suggestions.txt` / `fr_suggestions.txt` | 去重建议词，每行一条原文 |
| `de_unfinished.txt` / `fr_unfinished.txt` | 待完成的查询前缀，每行一条；全部完成时为空 |
| `de_details.json` / `fr_details.json` | 查询种子、完整前缀、时间、请求地址、建议顺序和词表行号 |
| `de_failures.json` / `fr_failures.json` | 未完成原因，区分失败和未执行 |
| `summary.md` | 各站成功数、无建议数、失败数、待完成数和去重词数 |
| `run.log` | 运行日志 |

只选择一个站点时，只导出该站点的文件。`.txt` 只存词或词组，不包含说明、编号、日志或统计。

明细中的 `suggestions` 使用 `rank` 记录该次建议顺序，`word_line` 指向同目录结果词表的行号，行号从 1 开始。同一建议在多个查询中出现时，各次记录都保留。

## 缓存和续跑

缓存位于 `cache/站点/`，按站点、类别和完整前缀区分：

- `<查询哈希>.txt`：该次查询的建议词，每行一条。
- `<查询哈希>.json`：时间、请求地址、原始接口响应、词数和词表校验值。

词表和元数据分别原子写入，读取时检查校验值，半写入或损坏的数据不会被当作有效缓存。失败查询不写成功缓存；接口成功返回空建议时会保存零条结果。

再次使用相同输入与扩展方式运行，会复用有效缓存。每次输出仅包含当前计划对应的结果，不混入其他输入的历史词表。Ctrl+C 会导出已完成的结果，意外退出后已落盘的缓存仍可复用。

HTTP 429 按服务端要求有限重试，仍失败则暂停该站点，剩余前缀留待下次运行。建议保留默认请求间隔，避免同时启动多份采集程序。

## 结果含义

建议词按原文精确去重，保留首次出现的顺序，不翻译或改写词组。结果代表记录时间该站点实际返回的建议，出现顺序不代表搜索量，也不能证明买家所在地。

## 接口来源

程序请求亚马逊域名下的搜索建议服务：

- 德国：`https://completion.amazon.de/api/2017/suggestions`
- 法国：`https://completion.amazon.fr/api/2017/suggestions`

这些地址通过实际 HTTP 请求验证可用。它们属于网站使用的搜索建议服务，未找到对应的官方开发者接口文档；不应将其视为有正式开发者支持承诺的开放 API。

`2017` 是 URL 路径中的固定部分，并非查询数据年份的参数。未找到亚马逊对这个数字命名含义的官方说明，因此不能确定它具体指哪次发布或版本。

## 退出状态

- `0`：本次请求均成功，或已达到 `--max-queries` 限额；未执行部分仍会列入汇总。
- `1`：存在失败查询，见失败明细。
- `2`：配置、输入或文件写入错误。
- `130`：用户按 Ctrl+C 中断。

## 测试

```powershell
python -B -m unittest discover -s nineTools/getSugWord -p test_get_sug_word.py -v
```
