# nineTools —— 独立小工具集

各工具按用途分目录存放，脚本与其配套输入/输出文件在同一目录内。

| 目录 | 工具 | 用途 |
|---|---|---|
| `color_size_change/` | `C&S_change.py` | 颜色/尺寸映射转换：德 → 原始数据 → 法（映射文件在仓库 `data/` 下；直接覆盖同目录 `color_change` / `size_change`） |
| `id_sorting/` | `id_sorting.py` | 对 12 位 id 按每位 ASCII 值升序排序（数据 `id_sorting_data` → 结果 `id_sorting_result`） |
| `random_id/` | `random_id.py` | 生成随机 ID（规则同流水线 assign_ids；>100 条自动落盘 `random_ids_*.txt`，不入库） |
| `sku_extract/` | `extract_sku.py` | 从抓取文本（`SKU3`）抽取「SKU」标记后的值，去重输出每行一个 |
| `zip/` | `zip_dir.py` | 压缩目录（默认 besskyproject/Means_of_production）到 `zip_by_ec/{当天日期}_{操作用户}.zip` |

## 运行

每个目录下直接运行（各自默认路径基于脚本所在目录）：
```bash
python color_size_change/C&S_change.py
python id_sorting/id_sorting.py
python random_id/random_id.py
python sku_extract/extract_sku.py
python zip/zip_dir.py
```

## 说明

- `random_ids_*.txt`（随机 ID 输出）与 SKU 抓取/结果文本不入库（见 `.gitignore` `nineTools/**/*.txt`）；
- `zip/` 的 zip 输出在仓库 `zip_by_ec/` 下，大文件不入库。
