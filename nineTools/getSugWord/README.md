# 亚马逊德国、法国和英国站搜索建议采集

通过亚马逊建议接口采集德国、法国和英国站搜索建议，只依赖 Python 3.10 及以上版本的标准库。

## 输入和配置

- `keywords_de.txt`：德国关键词，每行一个词或词组。
- `keywords_fr.txt`：法国关键词，每行一个词或词组。
- `keywords_uk.txt`：英国关键词，每行一个词或词组。
- `config.py`：所有默认配置，修改其中的 `SETTINGS` 字典即可。

首次检出仓库时，在本目录创建本地配置和对应站点的词表。例如只采集英国站，可在 `config.py` 写入 `SETTINGS = {"markets": ["uk"]}`，其余配置使用程序默认值。

词表保存为 UTF-8，支持 BOM。空行忽略，重复输入自动合并。输入词只用于查询，结果词表保留亚马逊实际返回的原文。

| 配置 | 默认值 | 含义 |
| --- | --- | --- |
| `markets` | `["de", "fr"]` | 采集站点，可选择 `de`、`fr`、`uk` |
| `category` | `"aps"` | 搜索类别，`aps` 为全部类别 |
| `expand` | `"none"` | `none` 原词；`letters` 字母扩展；`letters-digits` 字母及数字扩展 |
| `interval` | `1.2` | 请求间隔秒数，不得小于 0.5 |
| `timeout` | `15` | 单次请求超时秒数 |
| `retries` | `2` | 失败后的额外重试次数，范围 0 到 5 |
| `cache_hours` | `24` | 仅启用过程文件保存时生效；缓存有效小时数，0 表示每次重新采集 |
| `save_process_files` | `False` | 只保存结果词表；不保存缓存、日志、查询明细、待完成词表或统计 |

## 运行

统一使用 `get_sug_word.py` 运行。程序按所选站点读取 `keywords_<站点>.txt`。

在项目根目录执行：

```powershell
python nineTools/getSugWord/get_sug_word.py
```

首次运行前填写相应站点的词表，词表为空时程序会提示并停止。默认将接口返回的词去重后写入对应站点的结果文件，进度和统计显示在终端。

```powershell
# 单独采集一个站点
python nineTools/getSugWord/get_sug_word.py --market de
python nineTools/getSugWord/get_sug_word.py --market fr
python nineTools/getSugWord/get_sug_word.py --market uk

# 本次最多请求 5 个原词
python nineTools/getSugWord/get_sug_word.py --max-queries 5

# 使用另一份词表，须指定单个站点
python nineTools/getSugWord/get_sug_word.py --market de --input nineTools/getSugWord/keywords_de.txt

# 只看计划，不联网、不写输出
python nineTools/getSugWord/get_sug_word.py --dry-run
```

`letters` 对每个输入词生成最多 28 个前缀：原词、原词后加空格、原词后加空格和 a 到 z。`letters-digits` 额外增加 0 到 9，共最多 38 个前缀。查询前缀不会被自行当作建议词写入结果。

`--input` 只接受 `.txt`，相对路径以命令运行目录为准。`--config` 可指定另一份包含 `SETTINGS` 字典的 `.py` 配置，命令行参数覆盖配置中的同名选项。

## 输出格式

每次运行创建独立的 `outputs/时间戳/` 目录，保留之前的结果，不改动已有词表或手动清理后的结果。

| 文件 | 内容 |
| --- | --- |
| `de_suggestions.txt` / `fr_suggestions.txt` / `uk_suggestions.txt` | 去重建议词，每行一条原文 |

只选择一个站点时，只导出该站点的文件。`.txt` 只存词或词组，不包含说明、编号、日志或统计。

## 缓存和续跑

默认不读取或写入缓存。每次执行会重新请求原词；Ctrl+C 会导出当次已完成的结果，不保存待完成词表。

如需调试，可显式将 `save_process_files` 改为 `True`，启用缓存和查询明细等过程文件。当前配置保持 `False`。

HTTP 429 按服务端要求有限重试，仍失败则暂停该站点。失败原因和待完成数量显示在终端。建议保留默认请求间隔，避免同时启动多份采集程序。

## 结果含义

建议词按原文精确去重，保留首次出现的顺序，不翻译或改写词组。结果代表记录时间该站点实际返回的建议，出现顺序不代表搜索量，也不能证明买家所在地。

## 接口来源

程序请求亚马逊域名下的搜索建议服务：

- 德国：`https://completion.amazon.de/api/2017/suggestions`
- 法国：`https://completion.amazon.fr/api/2017/suggestions`
- 英国：`https://completion.amazon.co.uk/api/2017/suggestions`

这些地址通过实际 HTTP 请求验证可用。它们属于网站使用的搜索建议服务，未找到对应的官方开发者接口文档；不应将其视为有正式开发者支持承诺的开放 API。

`2017` 是 URL 路径中的固定部分，并非查询数据年份的参数。未找到亚马逊对这个数字命名含义的官方说明，因此不能确定它具体指哪次发布或版本。

## 退出状态

- `0`：本次请求均成功，或已达到 `--max-queries` 限额。
- `1`：存在失败查询，原因显示在终端。
- `2`：配置、输入或文件写入错误。
- `130`：用户按 Ctrl+C 中断。
