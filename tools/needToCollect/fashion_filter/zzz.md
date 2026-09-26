# 服装热词采集与清洗说明

运行 `hotwords_fashion.py` 会先向热词 API 采集，再按站点词根筛选；`clean_fashion.py` 只重跑本地清洗，不请求 API。**直接点 `main` 运行时，只需修改 [`site_config.py`](site_config.py) 顶部的 `DEFAULT_COUNTRY`**：`"de"` 为德国站，`"fr"` 为法国站。两个程序都会使用这同一个默认值。

```bash
python tools/needToCollect/fashion_filter/hotwords_fashion.py                  # 使用 DEFAULT_COUNTRY
python tools/needToCollect/fashion_filter/hotwords_fashion.py --country fr     # 临时覆盖为法国站
python tools/needToCollect/fashion_filter/clean_fashion.py                     # 用同一国家配置重洗最近数据
python tools/needToCollect/fashion_filter/clean_fashion.py --country fr --input path/to/raw.txt
```

站点参数仅支持 `de`、`fr`。`de/`、`fr/` 下分别维护四份 UTF-8 词根表：品类、属性、黑名单和品牌。表中每行一个词根、`#` 开头的行是注释；属性词以 `!` 开头表示可以单独保留，否则只在品类词同时命中时作为备注。黑名单优先于品类和属性，品牌按完整单词移除。当前匹配为不区分大小写的子串匹配，增补过短词根时要检查误报。

新数据分别写到 `raw/de/`、`raw/fr/` 和 `result/de/`、`result/fr/`。同日重复运行会生成新文件，不覆盖已有结果。旧版 `raw/`、`result/` 根目录下的德国站历史文件保留原位；独立清洗德国站时仍能自动读取旧版 `raw/` 文件。若指定 `--input`，请同时指定文件对应的 `--country`，避免用错误站点的规则清洗。

不联网验证：

```bash
python -m unittest discover -s tools/needToCollect/fashion_filter -p "test_*.py"
```
