# Prompts ImageGen finaux

Mode utilisé : outil ImageGen intégré. Les images de produit dans `sources/` ont servi de références de fidélité ; aucun texte n'a été demandé dans les générations, la typographie française a été composée ensuite dans `build_aplus.py`.

## Recalibrage L — prompt d'édition commun

Les six scènes ont ensuite été rééditées séparément avec le prompt invariant suivant, adapté à chaque pose :

```text
Use case: precise-object-edit.
Asset type: premium Amazon A+ fashion campaign source image.
Input images: Image 1 is the edit target. Image 2 is the exact khaki garment artwork reference. Image 3 is a same-cut hoodie silhouette/length reference with a different print; use it only for cut and length, never copy its colors or artwork. Image 4 is the size chart; use the L row, garment length 89 cm / 35.43 inches.
Primary request: change only the visible body length and lower-hem drape of every hoodie in Image 1 so it accurately represents size L. The main hem finishes on the lower thigh, about 8–15 cm above the kneecap. Only the narrow asymmetric front point may approach the top edge of the kneecap; it must never pass it.
Garment invariants: keep the oversized pointed hood, gray inner facing, khaki/taupe body, black smoky shoulders/cuffs/lower accents, exact small Nordic chest rune when visible, and exact large black roaring-beast back graphic when visible. Keep it clearly a lightweight longline hoodie/cardigan, not a trench coat or cape.
Scene invariants: preserve person identity, face, hair, expression, exact pose, body proportions, hands, legs, camera angle, framing, scenery, props, lighting, color grade and all background details.
Constraints: shorten and re-drape only the garment below the hip; keep sleeves and torso width unchanged; realistic fabric folds and shadows; no new accessories; no extra people; no text; no logo; no watermark; no weapons; no gore.
```

## 1 — Château / marche

```text
Use case: premium Amazon A+ fashion campaign.
Input images: Image 1 is the exact front-and-back garment reference; Image 2 is the exact back print reference.
Primary request: create a cinematic wide hero photograph of an adult male model wearing this exact khaki/taupe long hooded open-front cardigan costume, striding out of a massive medieval stone arch at midnight.
Garment fidelity: preserve the asymmetrical long hem, oversized pointed hood, gray inner front panel, khaki body, black smoky shoulders/cuffs/hem, small black Nordic rune symbol on the left chest, and the large black roaring beast graphic on the back. Do not redesign or simplify the garment.
Scene/backdrop: rain-polished cobblestones, distant ruined castle, low ground fog, carved pumpkins and amber lanterns only as small environmental accents.
Composition/framing: 16:9 ultra-wide campaign layout; full body, dynamic forward stride, coat hem caught by wind; model on the right third; generous clean dark negative space on the left for French headline overlay.
Lighting/mood: cool moon-blue rim light, warm amber torch light, deep charcoal shadows, premium editorial realism, dramatic but commercially clear.
Constraints: photorealistic; adult model; anatomically correct hands; no weapons, no text, no logos, no watermark, no gore, no mask; keep the garment clearly readable.
```

## 2 — Falaise nordique / retournement

```text
Use case: premium Amazon A+ fashion campaign.
Input images: Image 1 is the exact front-and-back garment reference; Image 2 is the exact back print reference.
Primary request: create a cinematic wide back-view product lifestyle photograph on a windswept Nordic cliff at blue hour. An adult male model wears the exact referenced khaki long hooded cardigan and is captured mid-turn while pulling the hood up with one hand; the large black roaring beast graphic is the central visual focus.
Garment fidelity: exact khaki/taupe color, oversized hood, long asymmetrical hem, black smoky shoulders and cuffs, original giant black roaring beast back print. Do not invent armor, fur, belts, buckles or leather panels.
Scene/backdrop: standing stones with subtle non-linguistic carved rune-like marks, distant storm sea, ravens very small in the sky, wind-blown fog.
Composition/framing: 16:9 wide, model on the right half, three-quarter back view, coat moving in wind; open left side for graphic text overlay.
Lighting/mood: cold silver sky, faint copper horizon glow, tactile woven fabric, premium realistic fashion photography.
Constraints: adult model, exact garment, realistic anatomy, no weapons, no text, no logos, no watermark, no gore.
```

## 3 — Ruelle aux lanternes / pas latéral

```text
Use case: premium Amazon A+ fashion campaign.
Input images: Image 1 is the exact front-and-back garment reference; Image 2 is the exact back print reference.
Primary request: create a cinematic wide fashion photograph in a lantern-lit old alley inspired by historical Japan at Halloween night. An adult male model wears the exact referenced khaki long hooded cardigan, captured in a fluid side-step while one hand brushes a dark wooden gate and the other rests naturally near the coat opening.
Garment fidelity: oversized pointed hood, gray inner panel, khaki body, black smoky gradient on shoulders/cuffs/hem, small Nordic rune symbol at left chest, long asymmetrical silhouette. Do not add armor, weapons, belts or costume accessories.
Scene/backdrop: wet stone lane, layered red-orange paper lanterns, drifting mist, subtle fallen maple leaves, deep indigo night.
Composition/framing: 16:9 wide, full-body three-quarter front view, lively diagonal perspective, subject left of center, clean darker right side for text.
Lighting/mood: red lantern glow versus cool indigo ambient light, rich color, editorial realism, readable product silhouette.
Constraints: adult model, anatomically correct hands, no text, no logos, no watermark, no gore, no weapon.
```

## 4 — Festival / rotation

```text
Use case: premium Amazon A+ Halloween fashion campaign.
Input images: Image 1 is the exact front-and-back garment reference; Image 2 is the exact back print reference.
Primary request: photorealistic wide night-festival fashion scene. An adult male model wearing the exact khaki long hooded cardigan is caught mid-spin in a lively European Halloween street festival, one foot pivoting and the asymmetrical coat panels sweeping outward, relaxed confident expression.
Garment fidelity: preserve the oversized pointed hood, gray inner front panels, khaki body, black smoky shoulders/cuffs/hem, left-chest Nordic rune symbol, long open front, and original back artwork. No redesign.
Scene/backdrop: colorful violet, teal and amber string lights, small pumpkin lantern stalls, tasteful costumed crowd only as soft bokeh, damp pavement, drifting theatrical haze.
Composition/framing: 16:9 wide, full body centered-right, motion in the coat hem, spacious darker left third for French copy.
Lighting/mood: celebratory, mysterious, saturated jewel colors, premium editorial photography, crisp fabric.
Constraints: adult model, realistic anatomy and hands, no weapons, no text, no logos, no watermark, no gore, no face paint.
```

## 5 — Bibliothèque gothique / pose assise

```text
Use case: premium Amazon A+ Halloween fashion campaign.
Input images: Image 1 is the exact front-and-back garment reference; Image 2 is the exact back print reference.
Primary request: cinematic wide interior fashion photograph inside an abandoned gothic library at night. An adult male model wears the exact khaki long hooded cardigan and sits casually on the edge of a massive wooden reading table, leaning forward with forearms relaxed on thighs, hood half-shadowing the face; the coat drapes naturally and the left-chest rune remains visible.
Garment fidelity: oversized pointed hood, gray inner front panels, khaki body, black smoky shoulders/cuffs/hem, small left-chest Nordic rune, asymmetrical long open hem. Do not add belts, armor, weapons, jewelry or extra costume pieces.
Scene/backdrop: tall dusty bookshelves, arched stained-glass window, floating dust, several warm candles at a safe distance, indigo moonlight, subtle red glass reflections.
Composition/framing: 16:9 wide, full seated figure on left half, strong diagonal table, open dark right side for typography, layered depth.
Lighting/mood: intellectual gothic mystery, warm candle pools against cool moonlight, tactile woven fabric, premium realistic fashion editorial.
Constraints: adult model, anatomically correct hands, no text, no logos, no watermark, no gore.
```

## 6 — Forêt / franchissement

```text
Use case: premium Amazon A+ Halloween fashion campaign.
Input images: Image 1 is the exact front-and-back garment reference; Image 2 is the exact back print reference.
Primary request: cinematic wide action photograph in an enchanted autumn forest at night. An adult male model wearing the exact khaki long hooded cardigan steps quickly across a low mossy stone wall, one arm extended naturally for balance, coat tails lifted by the movement, three-quarter front-to-side view.
Garment fidelity: preserve oversized pointed hood, gray inner front panel, khaki body, black smoky shoulders/cuffs/hem, small black Nordic rune on left chest, long asymmetric silhouette; do not add armor, belts or weapons.
Scene/backdrop: twisted old trees, copper leaves, emerald ground fog, tiny amber lanterns along a distant path, bright moon shafts through branches.
Composition/framing: 16:9 wide, dynamic low camera angle, full body on left-center, diagonal movement toward the viewer, clean darker right third for copy.
Lighting/mood: emerald, copper and moon-silver palette, energetic, cinematic, premium commercial realism, garment clearly readable.
Constraints: adult model, realistic anatomy, no text, no logos, no watermark, no gore, no weapons.
```
