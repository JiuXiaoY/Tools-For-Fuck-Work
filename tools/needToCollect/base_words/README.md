# base_words 基础词库

词库先按语言分目录，再按服装品类分文件：

- `de/`：德语基础词。
- `fr/`：法语基础词。
- `*_base_words`：每行一个可用于采集的词，文件内不加分类标题。
- `uncertain_base_words`：暂时无法确定品类或本身不是完整品类名的词；保留原文，不擅自修改。

整理规则：

1. 不改动原词的大小写、重音符号和拼写。
2. 明确的跨品类词移入对应品类文件。
3. 完全相同的重复词只保留一次。
4. `pants_base_words` 不再包含 shorts 和 leggings，因此不再需要额外维护 `pants_base_words_no_shorts`。
