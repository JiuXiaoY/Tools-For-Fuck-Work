# Amazon.de Premium A+ V2 — Editorial Night Theatre

本目录是针对“画面单调、动作重复”的重制版本。原版本未被覆盖；新版独立存放在 `v2_editorial`。

## 成品

- 14 张上传用 JPG。
- 10 张手机端上传图，位于 `mobile_600x450`，全部为 `600 × 450 px`。
- 7 个模块，严格使用 3 种高级 A+ 形式：全宽、三联图、全屏轮播。
- 全宽与轮播：`1464 × 600 px`。
- 三联图：`488 × 600 px`。
- 总览预览：`_preview/00-full-overview.jpg`。

## 视觉方向

- 字体语言参考用户提供的 Amazon.de 页面：手写刷字体、哥特展示字、粗窄体无衬线、橙红标签。仅提取视觉语言，没有复制竞品品牌、文案或版式。
- 四种动作：酒会举杯互动、户外台阶行走、后台侧坐整理袖口、穿过剧院幕布回身登台。
- 七种模块构图：电影首焦、浅色展廊拆解、三场景杂志封面、四色舞台轮播、对角线触感微距、三种实拍证据布局、浅色蓝图尺码表。
- 色彩：午夜蓝、琥珀橙、紫蓝舞台光、酒红、祖母绿、象牙白，避免整页只用同一暗色模板。

## 数据与真实性

- 产品设计、颜色、正背面、尺码数据仅取自 `enjinia_fr_20260922/enjinia/sources`。
- 未调用历史生成目录中的产品图或文案。
- 动态生活方式场景为本次新生成，基于源产品参考图；产品拆解、轮播证据窗、正背面与尺码页继续使用源图。
- 正式上传前建议复核 AI 场景中的局部纹样；商品真实性判断以源产品证据图为准。

## 上传顺序

1. `01-hero-1464x600.jpg`
2. `02-design-details-1464x600.jpg`
3. `03-01-cocktail-toast-488x600.jpg` + `03-02-festival-walk-488x600.jpg` + `03-03-backstage-cuff-488x600.jpg`
4. `04-01-carousel-navy-1464x600.jpg` 至 `04-04-carousel-burgundy-1464x600.jpg`
5. `05-material-craft-1464x600.jpg`
6. `06-01-worn-look-488x600.jpg` + `06-02-front-view-488x600.jpg` + `06-03-back-view-488x600.jpg`
7. `07-size-guide-de-1464x600.jpg`

`build_v2.ps1` 可重新生成全部图片和预览。

## 手机端对应关系

- 模块 1：`mobile_600x450/01-hero-mobile-600x450.jpg`
- 模块 2：`mobile_600x450/02-design-details-mobile-600x450.jpg`
- 模块 3：`mobile_600x450/03-scenes-triptych-mobile-600x450.jpg`
- 模块 4：`mobile_600x450/04-01...04-04` 四张轮播图
- 模块 5：`mobile_600x450/05-material-craft-mobile-600x450.jpg`
- 模块 6：`mobile_600x450/06-fit-triptych-mobile-600x450.jpg`
- 模块 7：`mobile_600x450/07-size-guide-mobile-600x450.jpg`

模块 3 和模块 6 的桌面端为横向三联，手机端重新排成上下三段，没有直接压缩桌面图。

