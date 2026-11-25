# Mirusen DE Premium A+ — Editorial V2

## Result

- 5 visually distinct Premium A+ modules.
- Each module has an independently composed desktop and mobile asset.
- Desktop exports: 1464 × 600 px.
- Mobile exports: 600 × 450 px.
- Every image is full bleed; no white side margins.
- The colour module uses a minimalist Mediterranean outdoor setting: heading at upper left, two worn lifestyle scenes below it, and five equal-ratio colour cards overlapping in a shallow fan on the right.
- The former `output` set was preserved. V2 exports are in `output_v2_editorial`.

## Generation mode

- Built-in ImageGen, raster image generation with image references.
- The revised colour module uses two additional built-in ImageGen backgrounds: `source_v2_editorial/03-colors-outdoor-background-desktop.png` and `source_v2_editorial/03-colors-outdoor-background-mobile.png`.
- `references/product-reference-01.jpg` was used only to preserve garment identity: half-zip collar, ivory/navy asymmetric construction, curved line motif, chest emblem, cognac shoulder/elbow patches, ribbed cuffs and hem.
- The five images in `../jessika_fr_20260920/generated_fr_20260922` were used only as editorial layout and module-diversity references.
- Desktop and mobile visuals were generated as separate compositions, not as crops of one master image.
- Final German typography, labels, size data, exact resizing, and JPEG export were applied deterministically by `build_editorial_v2.ps1`.

## Prompt set

Shared art direction: premium European menswear editorial, photorealistic commercial photography, warm ivory/stone architecture, navy and cognac accents, refined soft daylight, accurate fabric texture, complete edge-to-edge background, balanced Amazon Premium A+ layout, clean text-safe zones, no generated words, no extra logos, no watermark. Match the supplied garment reference only for product identity; create a new scene and composition.

1. Hero desktop — Wide editorial campaign image. Handsome male model wearing the reference half-zip on the left; a separate unworn front-view garment presentation on the right; Mediterranean stone arches and olive greenery; generous clean headline area across the upper middle; product and model both fully readable.
2. Hero mobile — 4:3 mobile-first composition. Three-quarter male model on the left and an independent garment-only presentation on the right; tall architectural framing and a compact upper-right title zone; preserve the complete pullover silhouette.
3. Details desktop — Premium product-feature board. Large garment-only front view on the left; five different macro panels on the right for collar/zip, cognac shoulder patch, chest emblem and curved lines, elbow patch, ribbed cuff/hem; elegant warm ivory botanical linework; empty label bands under every close-up.
4. Details mobile — Mobile-first feature board using the same five distinct details in a compact two-row grid; large product view on the left; readable empty caption bands; no reuse of the same crop.
5. Colours desktop — Photorealistic minimalist Mediterranean courtyard background with warm limestone, pale stucco, olive shadows and blue-sky depth. Upper-left title, two worn lifestyle scenes below, and five equal-size colour cards on the right in a symmetrical overlapping fan. A translucent glass layer, restrained navy circle and cognac arc add depth without covering the garments.
6. Colours mobile — Independently generated 4:3 Mediterranean terrace background with the same hierarchy. Compact upper-left title, two tall worn scenes below, and five equal-ratio colour cards overlapping in a balanced fan on the right.
7. Occasions desktop — Three-scene fashion triptych: office arrival with portfolio, city street walk, relaxed café weekend; the same hero garment identity but different body language, styling and environments; diagonal editorial dividers and bottom label zones.
8. Occasions mobile — Mobile-first three-panel triptych with full-height figures and clear office/city/café storytelling; independently reframed rather than cropped from desktop.
9. Size guide desktop — Warm ivory editorial information board with restrained navy/cognac botanical accents; a large clean empty data panel on the left and a faithful unworn product view on the right; no generated measurements or words.
10. Size guide mobile — 4:3 mobile information layout with clean table area on the left and smaller product view on the right; decorative corners kept away from the data area; no generated text.

## Final files

| Module | Desktop | Mobile |
|---|---|---|
| Hero | `01-hero-desktop-1464x600.jpg` | `01-hero-mobile-600x450.jpg` |
| Details | `02-details-desktop-1464x600.jpg` | `02-details-mobile-600x450.jpg` |
| Colours | `03-colors-desktop-1464x600.jpg` | `03-colors-mobile-600x450.jpg` |
| Occasions | `04-occasions-desktop-1464x600.jpg` | `04-occasions-mobile-600x450.jpg` |
| Size guide | `05-size-guide-desktop-1464x600.jpg` | `05-size-guide-mobile-600x450.jpg` |

## Size table used

All values are garment measurements in centimetres.

| Size | Bust | Shoulder | Sleeve | Length |
|---|---:|---:|---:|---:|
| S | 112 | 48 | 63 | 71 |
| M | 117 | 49.5 | 63.7 | 72 |
| L | 122 | 51 | 64.4 | 73 |
| XL | 127 | 52.5 | 65.1 | 74 |
| XXL | 132 | 54 | 65.8 | 75 |
| 3XL | 137 | 55.5 | 66.5 | 76 |
| 4XL | 142 | 57 | 67.2 | 77 |
| 5XL | 147 | 58.5 | 67.9 | 78 |
