# 法国套装热搜词研究

## 结论摘要

法国站“套装”检索不能只使用 `ensemble`。本次 AMZ123 法国站查询中，广义 `ensemble` 返回 190 条，经过项目通用清洗后仍有 171 条，其中 `femme` 44 条、`homme` 17 条、`other` 110 条；也就是说，约 64% 的清洗后结果仍是家具、床品、厨具、童装等非目标意图。适合实际使用的结构应当是“`ensemble/tailleur` + 人群 + 单品组合/场景/季节”。^1

最值得优先使用的三个词群是：通用与时尚场景的 `ensemble femme` / `ensemble femme chic et elegant`，正式场景的 `tailleur femme` / `tailleur pantalon femme`，以及运动场景的 `ensemble sport femme` / `ensemble survetement femme`。AMZ123 当前 `new_rank` 数据中，`ensemble femme chic et elegant` 排名 6,993，较旧排名改善 6,851 位；`ensemble sport femme` 排名 7,272，改善 428 位；`ensemble femme` 排名 9,179，改善 136 位。这里的数值是搜索词排名，不是搜索量。^1

本轮没有发现可称为“爆发词”的非品牌套装词。按项目配置的 `fluctuation < -60000` 严格阈值，`ensemble` 只留下品牌意图 `ensemble adidas homme`，`tailleur` 没有词通过阈值；品牌词已排除。因此本次交付应被理解为“当前有排名、可用于商品标题与词库扩展的热搜词”，不应表述成“短期暴涨词”。^1

## 研究范围与方法

研究对象是法国站成年服装套装，以女装外穿套装为主，补充男装词；排除内衣、睡衣、情趣、万圣节/历史服装、童装和纯品牌搜索。本地项目的 `hotwords.py` 被用作唯一采集入口，国家参数固定为 `fr`，主口径为 `new_rank`，并额外以 `fluctuation` 口径检查快速上升词。完整查询、返回数量、失败及零结果均记录在 [`fr_ensemble_queries_20260909.tsv`](fr_ensemble_queries_20260909.tsv)。

Google Trends 官方说明指出，不同拼写、单复数和同义词不会自动合并；因此 `ensemble 2 pieces`、`ensemble deux pieces`、`tailleur`、`costume` 等变体需要分别验证，不能把一个词的表现直接外推到另一个词。^2 本轮也确实观察到这种差异：`ensemble 2 pieces` 和 `ensemble deux pieces femme` 均无返回，但 `costume femme chic tailleur 3 pieces` 出现在 `tailleur` 与 `costume femme` 的结果中。^1

零售站点用于验证词义和商品供给，而不是替代热度数据。Zalando 将 `tailleur femme` 描述为由结构化外套搭配裤装或裙装的女装组合，并为 `tailleur pantalon femme` 展示超过千件商品，说明 `tailleur` 与 `tailleur pantalon` 是法国正式套装的成熟商品语言。^3 ^4 La Redoute 同样把 `ensemble tailleur pantalon femme` 用于职业、晚宴和正式场景，并明确使用 `costume deux pièces` 描述两件套。^5

运动套装方面，Decathlon 的 `ensemble sport femme` 页面展示 140 件商品，并区分 `ensemble survêtement` 与 `leggings + crop top`；这与 AMZ123 返回的 `ensemble sport femme`、`ensemble jogging femme`、`ensemble survetement femme`、`ensemble pilates femme` 和 `ensemble yoga femme` 一致。^6

## 优先词群

### A 级：直接进入核心词库

| 词群 | 建议关键词 | 证据与用途 |
|---|---|---|
| 通用 | `ensemble femme` | 广义核心词；AMZ123 当前排名 9,179，适合类目词和标题骨架。^1 |
| Chic | `ensemble femme chic et elegant` | 本轮套装相关词中排名最靠前，且较旧排名明显改善；适合通勤、宴会、休闲正装。^1 |
| 正式套装 | `tailleur femme` | 精准度高：定向查询 10/10 为 femme；广义 tailleur 查询 18 条中 15 条为 femme。^1 |
| 裤装西服 | `tailleur pantalon femme`、`tailleur femme ensemble pantalon` | AMZ123 有直接返回，Zalando 和 La Redoute 均有成熟商品页。^1 ^4 ^5 |
| 上衣+裤装 | `ensemble pantalon femme`、`ensemble femme pantalon et haut fluide` | 描述两件套结构，意图比单独 `ensemble` 明确。^1 |
| 运动 | `ensemble sport femme`、`ensemble de sport femme` | AMZ123 排名靠前，Decathlon 商品供给充分。^1 ^6 |
| 运动休闲 | `ensemble jogging femme`、`ensemble survetement femme` | 定向查询均有返回，适合卫衣/外套+长裤组合。^1 |
| 季节材质 | `ensemble femme ete`、`ensemble lin femme` | 适合夏季轻薄套装；使用无重音的热搜原词保存。^1 |

### B 级：按商品属性选用

- 正式与婚礼：`ensemble tailleur femme`、`ensemble tailleur femme mariage`、`tailleur femme pour mariage`、`tailleur femme mariage`、`tailleur femme chic`、`costume femme chic tailleur 3 pieces`。
- 休闲组合：`ensemble femme chic`、`ensemble chic femme`、`ensemble short femme`、`ensemble jupe et haut femme`、`ensemble femme pantalon et haut`。
- 运动细分：`ensemble pilates femme`、`ensemble yoga femme`、`ensemble running femme`、`tenue sport femme ensemble fitness`。
- 颜色与季节：`ensemble blanc femme chic`、`ensemble vert sauge femme`、`ensemble femme automne`。
- 人群细分：`tailleur femme pour mariage grande taille`、`ensemble sport femme musulmane`。这些词意图明确，但仅应在商品确实符合时使用。

### 男装补充

广义查询确认了 `ensemble homme`、`ensemble homme ete`、`ensemble jogging homme`、`ensemble sport homme`、`ensemble survetement homme`、`ensemble lin homme`、`ensemble homme hiver` 和 `ensemble de travail homme`。其中 `ensemble homme` 当前排名 9,287，较旧排名改善 776 位。男装词已独立放在最终词表的补充区，不与女装核心词混用。^1

## 待观察词与零结果

`ensemble coordonne femme` 在本轮 AMZ123 精确查询中无返回，但 La Redoute 存在明确的 `Ensemble coordonné femme` 商品入口，因此它属于“零售语义成立、当前热词证据不足”的扩展词，适合保留观察，不进入 A 级词库。^7

`ensemble 2 pieces femme`、`ensemble deux pieces femme`、`ensemble 3 pieces femme`、`ensemble femme mariage` 和 `ensemble femme grande taille` 的精确查询没有稳定返回。不能因此断言没有需求：长尾组合 `ensemble femme chic et elegant mariage`、`tailleur femme pour mariage grande taille` 和 `costume femme chic tailleur 3 pieces` 均在更宽查询中出现。更合适的做法是保存长尾原词，而不是人为拼接没有数据支持的短词。^1

## 排除规则

以下词虽出现在广义结果中，但不应进入成年外穿套装词库：

- 内衣与情趣：包含 `lingerie`、`sous vetement`、`sexy`、`erotique`、`coquine`。
- 睡衣：包含 `pyjama`。
- 童装：包含 `enfant`、`fille`、`garcon`、`bebe`。
- 角色与节庆服装：包含 `halloween`、`moyen age`。
- 纯品牌意图：例如严格涨幅口径唯一命中的 `ensemble adidas homme`。
- 非套装部件：`veste tailleur femme`、`pantalon costume femme` 可作为单品词，但不能直接当作完整套装词。

尤其要谨慎使用 `costume femme`：法国零售语境中它可能指正式女装西服，但 AMZ123 定向结果同时包含万圣节和中世纪服装。若商品是正式套装，应优先使用 `tailleur femme`、`tailleur pantalon femme` 或更完整的 `costume femme chic tailleur 3 pieces`。

## 文件交付与使用建议

- [`../base_words/fr/ensemble_base_words`](../base_words/fr/ensemble_base_words)：后续复采用基础词，一行一词。
- [`../result/20260909_fr_ensemble_curated.txt`](../result/20260909_fr_ensemble_curated.txt)：人工筛选后的最终词表，按女装优先级、男装补充、待观察和排除意图分组。
- [`fr_ensemble_queries_20260909.tsv`](fr_ensemble_queries_20260909.tsv)：全部查询状态、数量和对应原始采集结果索引。
- `../result/20260909_101509_fr.txt`：广义 `ensemble` 主样本；保留噪声，供复核清洗规则。
- `../result/20260909_101513_fr.txt`：广义 `tailleur` 主样本；用于正式套装词复核。

标题或搜索词投放时，建议每件商品只选择与实物一致的一个核心结构词，再叠加场景、季节、材质或颜色。不要把 `chic`、`mariage`、`sport`、`musulmane`、`grande taille` 等互不相容的修饰词全部堆入同一标题。

## Sources

1. AMZ123. “[Hotwords Search API](https://api.amz123.com/search/v1/hotwords/search).” France (`country=fr`) direct POST query results, accessed September 9, 2026. Archived locally in `tools/needToCollect/result/20260909_*_fr.txt`; query inventory in `fr_ensemble_queries_20260909.tsv`.
2. Google Trends Help. “[Comparer des termes de recherche dans Google Trends](https://support.google.com/trends/answer/4359550?hl=fr).” Accessed September 9, 2026.
3. Zalando France. “[Tailleur Femme](https://www.zalando.fr/femme/?q=tailleur+femme).” Accessed September 9, 2026.
4. Zalando France. “[Tailleur pantalon femme](https://www.zalando.fr/mode-femme/?q=tailleur+pantalon+femme).” Accessed September 9, 2026.
5. La Redoute. “[Ensemble tailleur pantalon femme](https://www.laredoute.fr/lndng/ctlg.aspx?artcl=ensemble-tailleur-pantalon-femme).” Accessed September 9, 2026.
6. Decathlon France. “[Ensemble sport femme](https://www.decathlon.fr/vc/ensemble-sport-femme).” Accessed September 9, 2026.
7. La Redoute. “[Ensemble coordonné femme](https://www.laredoute.fr/lndng/ctlg.aspx?artcl=ensemble-coordonne-femme).” Accessed September 9, 2026.
