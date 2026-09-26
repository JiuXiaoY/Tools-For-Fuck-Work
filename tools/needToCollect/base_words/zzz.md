# base_words 基础词库说明

词库先按语言分目录（`de/`、`fr/`），**文件名 = `y_addr&yass/de_feasibility_domain` 下的 domain 目录名 + `_base.md`**：

```
de/coat_base.md        de/dress_base.md       de/top_base.md      de/pants_base.md
de/tractsuit_base.md   de/festival_base.md    de/fitnessTop_base.md

fr/coat_base.md        fr/dress_base.md       fr/top_base.md      fr/pants_base.md
fr/tractsuit_base.md
```

（`coat/longTitle` 等 domain 尚无可提炼的基础词，暂不建空文件。）

格式：

- 全部为 `.md` 文件，UTF-8 无 BOM。
- 文件内用 `## <子品类>` 分节；**同属一个大品类的子品类合并在同一个文件里**（如上装类的 shirt / sweatshirt / weste 都在 `top_base.md`）。
- **第一个 `##` 紧贴文件首行，其后的每个 `##` 上方空一行**；节标题下直接跟词，词与词之间不留空行。
- 除 `##` 节标题外，**每行一个可直接用于采集的词**；不写其它注释。
- `## link`：**出现在源文件里、但不属于本 domain 的其它品类词**（如 `BH`、`Dessous`、`Crop Top`、`Rock`、`Kostüm`…），集中放在文件末尾的 `## link` 节，供跨品类关联参考，不计入本 domain 的采集词。
- `festival_base.md`：节日/主题类（Halloween、Oktoberfest、Kostüm…），本身不是一个服装部位，故单独成文件。

## 归类对应关系（旧 → 新）

| 旧文件 | 新位置 |
|---|---|
| `de/coat_base_words` | `de/coat_base.md` → `## jacke` `## mantel` `## poncho` |
| `de/dress_base_words`、`de/skirt_base_words`、`de/jumpsuit_base_words` | `de/dress_base.md` → `## kleid` `## rock` `## jumpsuit` |
| `de/shirt_base_words`、`de/sweatshirt_base_words`、`de/vest_base_words` | `de/top_base.md` → `## shirt` `## sweatshirt` `## weste` |
| `de/pants_base_words`、`de/shorts_base_words`、`de/leggings_base_words` | `de/pants_base.md` → `## hose` `## jeans` `## shorts` `## leggings` |
| `de/set_base_words`、`de/functional_suit_base_words` | `de/tractsuit_base.md` → `## sportanzug` `## anzug` `## zweiteiler` `## pyjama` `## funktionsanzug` |
| `de/uncertain_base_words` | 拆为 `de/festival_base.md`（Halloween、Oktoberfest、Kleopatra Kostüm）、`de/top_base.md` `## details`（Halbreißverschluss、Viertelreißverschluss、Kapuzen）；其余 4 个无法归类的词（Schutz、Fleece、Strick、Taktische）不再保留 |
| `fr/coat_base_words` | `fr/coat_base.md` → `## veste` `## manteau` `## blouson` `## parka` `## doudoune` `## coupe-vent` `## base` `## lot` |
| `fr/dress_base_words` | `fr/dress_base.md` → `## robe` |
| `fr/knitwear_base_words`、`fr/shirt_base_words`、`fr/workwear_base_words` | `fr/top_base.md` → `## maille` `## chemise` `## t-shirt` `## haut` `## travail`（Blouse de chef） |
| `fr/pants_base_words` | `fr/pants_base.md` → `## pantalon` |
| `fr/set_base_words`、`fr/workwear_base_words` | `fr/tractsuit_base.md` → `## ensemble` `## tailleur` `## travail`（Uniforme de travail） |
| （新增，非搬运）`y_addr&yass/de_data_pool/bestseller/corset` | `de/fitnessTop_base.md` → `## korsett` `## korsett-form` `## korsett-oberteil` `## korsett-kleid` `## taillenformer` `## shapewear`：从该 bestseller 池的 100 条标题里提炼实际出现的品类词（Korsett/Corsage/Bustier 家族、Unterbrust·Vollbrust·Halbbrust·Überbrust/Overbust 覆盖型、Korsettkleid·Corsagenkleid、Taillenformer·Taillenmieder·Cincher·Waist Trainer、Body Shaper·Shapewear），不是从旧 `*_base_words` 搬运；原文中空格写法与连写写法并存的（`Korsett-Top`/`Korsett Top`、`Korsettkleid`/`Korsett Kleid`、`Unterbrustkorsett`/`Unterbrust Korsett`、`Überbrustkorsett`/`Überbrust Korsett`）两种都保留；原文出现但不属于本 domain 的其它品类词收进末尾 `## link` |

整理规则：

1. 不改动原词的大小写、重音符号和拼写（复数形式如 `Kleider`、`Abendkleider` 原样保留）。
2. 只做搬运和分节：不删词、不造词、不改词。重组前后逐词核对，词表多重集完全一致（de 284 词、fr 135 词；随后按需求删除了 `de/uncertain_base.md`，其 4 个词不再计入）。
3. 无同名 domain 目录的品类，按「属于哪个部位」并入：skirt / jumpsuit → dress；functional_suit / set → tractsuit；workwear 拆开（Blouse de chef → top，Uniforme de travail → tractsuit）。
4. 合并前的原始 `*_base_words` 文件已从工作区删除；它们仍留在 git 历史中（如 `git show HEAD:tools/needToCollect/base_words/de/coat_base_words`），需要回退直接取用。
5. 同一文件内完全相同的重复词只保留一次。
6. 同一个词的空格写法与连写/连字符写法**同时存在时都要保留**（如 `Korsett-Top` 与 `Korsett Top`、`Korsettkleid` 与 `Korsett Kleid`、`Unterbrustkorsett` 与 `Unterbrust Korsett`），不做归一化合并。
