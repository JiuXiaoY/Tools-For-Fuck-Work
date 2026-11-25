# Amazon.es 女巫裙 Premium A+ 视觉稿

为 `dressHa_es_000000` 制作的 7 个西班牙语高级完整图片模块。桌面图为 **1464 × 600 px**；对应的手机图在 `mobile_600x450/`，尺寸为 **600 × 450 px**。按文件名前缀 `01` 至 `07` 顺序上传。`UPLOAD_INFO.csv` 列出模块、文件名、西班牙语替代文字和 AI 人物标记。

## 预览

- `_preview/00-desktop-overview.png`
- `_preview/00-mobile-overview.png`

## 视觉方向

- 黑紫、古铜橙和羊皮纸色构成万圣节配色。展示标题使用 `Baskerville Old Face` 与少量 `Old English Text MT`；说明文字使用高对比、易读的字体。
- 两张 `_generated/` 场景图基于原商品照片生成，只用于氛围和穿着情景。模块 `02`、`04`、`06`、`07` 保留源照片作为款式证据。
- 文案仅描述照片可核实的黑色、长款、修身鱼尾轮廓、翼状宽袖、圆领和下摆尖角；尺码取自 `photo/51pJ+3deYDL._AC_SX679_.jpg`。
- 原商品链接见上级目录 `link.md`。用户提供的 Amazon.de 页面只作为字体与排版方向参考，未复制其品牌、文案或图片。

## 模块

| 顺序 | 文件前缀 | 内容 |
| --- | --- | --- |
| 1 | `01-hero` | 万圣节主视觉 |
| 2 | `02-silhouette` | 实物轮廓与三个设计特征 |
| 3 | `03-threshold` | 门廊情景图 |
| 4 | `04-design-details` | 翼袖、领口、下摆特写 |
| 5 | `05-occasions` | 三种使用场景 |
| 6 | `06-size-guide` | S–XXXL 尺码表，厘米 |
| 7 | `07-finale` | 收尾主张与实物照 |

## 上传前检查

- 模块 `01`、`03`、`05` 含写实 AI 生成人物，JPEG 的 XMP `dc:subject` 已写入 `contains-synthetic-performer`。上传到亚马逊素材库时仍应确认该标记被识别。
- 两张生成场景图可能与实物在局部面料、后领口或裙摆褶皱上有差异；以 `photo/` 中的原始商品图为准。
- 商品原图最长边仅约 679 px；需要更高清的原始拍摄图才能进一步改善实物特写清晰度。
- 本目录是待审核的上传素材，尚未提交或发布到亚马逊。

## 重建

在可用 Python 与 Playwright Chromium 的环境中运行：

```powershell
python build_aplus.py
```

排版源文件为 `build_aplus.py`（HTML/CSS）；生成场景的提示词见 `PROMPTS.md`。
