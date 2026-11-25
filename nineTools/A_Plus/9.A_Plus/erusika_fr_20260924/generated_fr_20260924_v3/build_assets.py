from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent
SCENES = ROOT / "_scenes"
DESKTOP = (1464, 600)
MOBILE = (600, 450)

FONT = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_SB = Path(r"C:\Windows\Fonts\seguisb.ttf")
FONT_B = Path(r"C:\Windows\Fonts\segoeuib.ttf")

INK = (19, 22, 25, 255)
WHITE = (255, 255, 255, 255)
IVORY = (246, 243, 237, 255)
DENIM = (77, 111, 139, 255)
PALE = (231, 234, 235, 255)


def font(size: int, style: str = "regular") -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str({"regular": FONT, "semibold": FONT_SB, "bold": FONT_B}[style]), size)


def cover(image: Image.Image, size: tuple[int, int], fx: float = 0.5, fy: float = 0.5) -> Image.Image:
    image = image.convert("RGB")
    scale = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    x = max(0, min(round((resized.width - size[0]) * fx), resized.width - size[0]))
    y = max(0, min(round((resized.height - size[1]) * fy), resized.height - size[1]))
    return resized.crop((x, y, x + size[0], y + size[1]))


def contain(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    image = image.convert("RGBA")
    scale = min(size[0] / image.width, size[1] / image.height)
    return image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)


def scene(name: str, size: tuple[int, int], fx: float = 0.5, fy: float = 0.5) -> Image.Image:
    return cover(Image.open(SCENES / name), size, fx, fy).convert("RGBA")


def gradient(size: tuple[int, int], color=(8, 12, 16), max_alpha=205, reverse=False) -> Image.Image:
    w, h = size
    strip = Image.new("RGBA", (w, 1))
    px = strip.load()
    for x in range(w):
        t = x / max(1, w - 1)
        if reverse:
            t = 1 - t
        a = round(max_alpha * (1 - t) ** 1.7)
        px[x, 0] = (*color, a)
    return strip.resize((w, h), Image.Resampling.BILINEAR)


def bottom_gradient(size: tuple[int, int], max_alpha=190) -> Image.Image:
    w, h = size
    strip = Image.new("RGBA", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(1, h - 1)
        px[0, y] = (7, 10, 13, round(max_alpha * t ** 2))
    return strip.resize((w, h), Image.Resampling.BILINEAR)


def headline(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], size: int, fill=WHITE, anchor="la") -> None:
    draw.text(xy, text, font=font(size, "bold"), fill=fill, anchor=anchor)


def subhead(draw: ImageDraw.ImageDraw, text: str, xy: tuple[int, int], size: int, fill=(220, 231, 239, 255), anchor="la") -> None:
    draw.text(xy, text, font=font(size, "semibold"), fill=fill, anchor=anchor)


def pill(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], dark=True, size=16) -> None:
    bg = (12, 16, 20, 218) if dark else (249, 247, 242, 225)
    fg = WHITE if dark else INK
    draw.rounded_rectangle(box, radius=(box[3] - box[1]) // 2, fill=bg, outline=(255, 255, 255, 80), width=1)
    bbox = draw.textbbox((0, 0), text, font=font(size, "semibold"))
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((box[0] + box[2] - tw) / 2, (box[1] + box[3] - th) / 2 - bbox[1]), text, font=font(size, "semibold"), fill=fg)


def rounded_panel(base: Image.Image, image: Image.Image, box: tuple[int, int, int, int], fx=0.5, fy=0.5, radius=24) -> None:
    x0, y0, x1, y1 = box
    panel = cover(image, (x1 - x0, y1 - y0), fx, fy).convert("RGBA")
    mask = Image.new("L", panel.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, panel.width, panel.height), radius=radius, fill=255)
    panel.putalpha(mask)
    shadow = Image.new("RGBA", panel.size, (0, 0, 0, 90))
    shadow.putalpha(mask.point(lambda a: round(a * 0.35)))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)), (x0 + 8, y0 + 10))
    base.alpha_composite(panel, (x0, y0))


def cutout_white(image: Image.Image) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.int16)
    delta = 255 - arr.min(axis=2)
    alpha = np.clip((delta - 5) * 13, 0, 255).astype(np.uint8)
    alpha_image = Image.fromarray(alpha, "L").filter(ImageFilter.GaussianBlur(0.7))
    result = image.convert("RGBA")
    result.putalpha(alpha_image)
    bbox = alpha_image.point(lambda a: 255 if a > 18 else 0).getbbox()
    return result.crop(bbox) if bbox else result


FLAT = Image.open(SRC / "61hADjeEJIL._AC_SX679_.jpg").convert("RGB")
FLAT_CUTOUT = cutout_white(FLAT)


def paste_cutout(base: Image.Image, item: Image.Image, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    fitted = contain(item, (x1 - x0, y1 - y0))
    x = x0 + (x1 - x0 - fitted.width) // 2
    y = y0 + (y1 - y0 - fitted.height) // 2
    shadow = Image.new("RGBA", fitted.size, (0, 0, 0, 100))
    shadow.putalpha(fitted.getchannel("A").point(lambda a: round(a * 0.40)))
    base.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(12)), (x + 10, y + 12))
    base.alpha_composite(fitted, (x, y))


def module_01(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    if mobile:
        base = scene("hero-city.png", size, 0.78, 0.50)
        base.alpha_composite(bottom_gradient(size, 210))
        draw = ImageDraw.Draw(base)
        subhead(draw, "CONTRASTES AFFIRMÉS", (34, 352), 16)
        headline(draw, "EN MOUVEMENT", (34, 378), 34)
    else:
        base = scene("hero-city.png", size, 0.50, 0.50)
        base.alpha_composite(gradient((730, 600), max_alpha=190), (0, 0))
        draw = ImageDraw.Draw(base)
        subhead(draw, "CONTRASTES AFFIRMÉS", (80, 198), 22)
        headline(draw, "LIGNES MODERNES", (80, 235), 55)
        headline(draw, "EN MOUVEMENT", (80, 298), 55)
        draw.line((80, 374, 485, 374), fill=(199, 218, 232, 255), width=3)
    return base


def module_02(size: tuple[int, int]) -> Image.Image:
    source = Image.open(SCENES / "front-back-studio.png")
    mobile = size == MOBILE
    if mobile:
        base = Image.new("RGBA", size, (228, 229, 227, 255))
        rounded_panel(base, source.crop((0, 0, source.width // 2 + 60, source.height)), (12, 16, 294, 434), 0.50, 0.48, 18)
        rounded_panel(base, source.crop((source.width // 2 - 60, 0, source.width, source.height)), (306, 16, 588, 434), 0.50, 0.48, 18)
        draw = ImageDraw.Draw(base)
        pill(draw, "VUE DE FACE", (28, 382, 278, 426), size=12)
        pill(draw, "VUE DE DOS", (322, 382, 572, 426), size=12)
    else:
        base = cover(source, size).convert("RGBA")
        base.alpha_composite(bottom_gradient(size, 145))
        draw = ImageDraw.Draw(base)
        headline(draw, "DE FACE & DE DOS", (732, 530), 38, anchor="ma")
        pill(draw, "VUE DE FACE", (178, 506, 430, 558), size=16)
        pill(draw, "VUE DE DOS", (1034, 506, 1286, 558), size=16)
    return base


def module_03(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    if mobile:
        base = scene("cuff-detail-boutique.png", size, 0.44, 0.50)
        base.alpha_composite(bottom_gradient(size, 210))
        draw = ImageDraw.Draw(base)
        headline(draw, "DÉTAILS EN ACTION", (300, 354), 30, anchor="ma")
        pill(draw, "REVERS • POIGNETS • POCHES", (76, 397, 524, 439), size=12)
    else:
        base = scene("cuff-detail-boutique.png", size, 0.50, 0.50)
        base.alpha_composite(gradient((560, 600), max_alpha=175, reverse=True), (904, 0))
        draw = ImageDraw.Draw(base)
        subhead(draw, "DÉTAILS VISIBLES", (1390, 220), 19, anchor="ra")
        headline(draw, "DÉTAILS", (1390, 258), 48, anchor="ra")
        headline(draw, "EN ACTION", (1390, 314), 48, anchor="ra")
        pill(draw, "REVERS • POIGNETS • POCHES", (985, 395, 1390, 447), size=15)
    return base


def module_04(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    if mobile:
        base = scene("lifestyle-cafe.png", size, 0.72, 0.50)
        base.alpha_composite(bottom_gradient(size, 215))
        draw = ImageDraw.Draw(base)
        subhead(draw, "AU QUOTIDIEN", (34, 352), 16)
        headline(draw, "ALLURE DÉCONTRACTÉE", (34, 381), 30)
    else:
        base = scene("lifestyle-cafe.png", size, 0.50, 0.50)
        base.alpha_composite(gradient((710, 600), max_alpha=168), (0, 0))
        draw = ImageDraw.Draw(base)
        subhead(draw, "AU QUOTIDIEN", (78, 208), 21)
        headline(draw, "ALLURE", (78, 246), 53)
        headline(draw, "DÉCONTRACTÉE", (78, 308), 53)
        draw.text((78, 384), "Un look en mouvement aux contrastes affirmés", font=font(21), fill=(233, 238, 241, 255))
    return base


SIZE_ROWS = [
    ("S", "106 cm / 41.73\"", "60 cm / 23.62\"", "80 cm / 31.50\""),
    ("M", "112 cm / 44.09\"", "61 cm / 24.02\"", "82 cm / 32.28\""),
    ("L", "118 cm / 46.46\"", "62 cm / 24.41\"", "84 cm / 33.07\""),
    ("XL", "124 cm / 48.82\"", "63 cm / 24.80\"", "86 cm / 33.86\""),
    ("XXL", "130 cm / 51.18\"", "64 cm / 25.20\"", "88 cm / 34.65\""),
]


def size_table(base: Image.Image, box: tuple[int, int, int, int], mobile=False) -> None:
    draw = ImageDraw.Draw(base)
    x0, y0, x1, y1 = box
    xs = [x0, x0 + round((x1 - x0) * 0.13), x0 + round((x1 - x0) * 0.44), x0 + round((x1 - x0) * 0.72), x1]
    row_h = (y1 - y0) / 6
    data = [("Taille", "Poitrine", "Manche", "Longueur")] + SIZE_ROWS
    for r in range(6):
        ya, yb = round(y0 + r * row_h), round(y0 + (r + 1) * row_h)
        draw.rectangle((x0, ya, x1, yb), fill=DENIM if r == 0 else ((249, 247, 243, 245) if r % 2 else (228, 232, 234, 245)))
    for x in xs:
        draw.line((x, y0, x, y1), fill=(130, 139, 145, 255), width=1)
    for r in range(7):
        y = round(y0 + r * row_h)
        draw.line((x0, y, x1, y), fill=(130, 139, 145, 255), width=1)
    for r, row in enumerate(data):
        for c, value in enumerate(row):
            f = font(10 if mobile else 15, "semibold" if r else "bold")
            bbox = draw.textbbox((0, 0), value, font=f)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            cell = (xs[c], round(y0 + r * row_h), xs[c + 1], round(y0 + (r + 1) * row_h))
            draw.text(((cell[0] + cell[2] - tw) / 2, (cell[1] + cell[3] - th) / 2 - bbox[1]), value, font=f, fill=WHITE if r == 0 else INK)


def module_05(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    if mobile:
        base = Image.new("RGBA", size, (237, 239, 239, 255))
        hero = scene("hero-city.png", (600, 165), 0.80, 0.50)
        base.alpha_composite(hero, (0, 285))
        draw = ImageDraw.Draw(base)
        headline(draw, "GUIDE DES TAILLES & COUPE", (300, 18), 26, INK, "ma")
        subhead(draw, "Mesures du vêtement", (300, 54), 14, DENIM, "ma")
        size_table(base, (18, 86, 582, 276), True)
        draw.rounded_rectangle((30, 316, 380, 426), radius=16, fill=(249, 247, 243, 225))
        draw.text((52, 337), "Comparez avant l’achat", font=font(17, "semibold"), fill=INK)
        draw.text((52, 373), "Poitrine • Manche • Longueur", font=font(13), fill=(59, 64, 68, 255))
    else:
        base = scene("hero-city.png", size, 0.55, 0.50)
        base.alpha_composite(Image.new("RGBA", size, (238, 240, 240, 158)))
        draw = ImageDraw.Draw(base)
        draw.rounded_rectangle((38, 34, 1026, 566), radius=28, fill=(244, 245, 244, 235))
        headline(draw, "GUIDE DES TAILLES & COUPE", (532, 61), 38, INK, "ma")
        subhead(draw, "Mesures du vêtement", (532, 108), 18, DENIM, "ma")
        size_table(base, (72, 155, 992, 495), False)
        draw.text((72, 519), "Comparez les mesures avec un vêtement similaire avant l’achat.", font=font(16), fill=(53, 57, 61, 255))
    return base


def carousel_01(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    base = Image.new("RGBA", size, (18, 22, 26, 255))
    draw = ImageDraw.Draw(base)
    w, h = size
    draw.polygon([(0, h), (round(w * .42), 0), (round(w * .55), 0), (round(w * .13), h)], fill=(55, 83, 104, 90))
    collar = FLAT.crop((70, 0, 630, 390))
    placket = FLAT.crop((125, 160, 590, 690))
    cuff = FLAT.crop((0, 340, 315, 790))
    if mobile:
        headline(draw, "DÉTAILS À LA LOUPE", (300, 20), 28, WHITE, "ma")
        rounded_panel(base, collar, (18, 68, 582, 258), 0.50, 0.44, 20)
        rounded_panel(base, placket, (18, 276, 294, 432), 0.50, 0.50, 18)
        rounded_panel(base, cuff, (306, 276, 582, 432), 0.43, 0.54, 18)
        pill(draw, "REVERS & BOUTONNAGE", (122, 210, 478, 250), size=12)
        pill(draw, "POCHE AVANT", (55, 387, 257, 425), size=11)
        pill(draw, "POIGNET REPLIÉ", (347, 387, 547, 425), size=11)
    else:
        subhead(draw, "PLANCHE 01", (58, 45), 18, (142, 176, 201, 255))
        headline(draw, "STRUCTURE", (58, 78), 42)
        headline(draw, "& DÉTAILS", (58, 127), 42)
        rounded_panel(base, collar, (34, 202, 854, 570), 0.50, 0.46, 28)
        rounded_panel(base, cuff, (890, 30, 1430, 286), 0.43, 0.53, 24)
        rounded_panel(base, placket, (890, 314, 1430, 570), 0.50, 0.50, 24)
        pill(draw, "REVERS & BOUTONNAGE", (472, 506, 825, 558), size=15)
        pill(draw, "POIGNET REPLIÉ", (968, 226, 1352, 274), size=14)
        pill(draw, "POCHE AVANT", (1018, 510, 1302, 558), size=14)
    return base


def carousel_02(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    source = Image.open(SCENES / "couple-triptych.png")
    if mobile:
        base = cover(source, size, 0.50, 0.50).filter(ImageFilter.GaussianBlur(12)).convert("RGBA")
        base.alpha_composite(Image.new("RGBA", size, (10, 13, 16, 112)))
        lineup = contain(source, (580, 280))
        x, y = (600 - lineup.width) // 2, 86 + (280 - lineup.height) // 2
        shadow = Image.new("RGBA", lineup.size, (0, 0, 0, 95)).filter(ImageFilter.GaussianBlur(10))
        base.alpha_composite(shadow, (x + 6, y + 8))
        base.alpha_composite(lineup, (x, y))
        draw = ImageDraw.Draw(base)
        headline(draw, "TROIS MOMENTS", (300, 24), 30, WHITE, "ma")
        pill(draw, "UN MÊME LOOK", (112, 382, 488, 430), size=14)
    else:
        base = cover(source, size, 0.50, 0.50).convert("RGBA")
        base.alpha_composite(bottom_gradient(size, 150))
        draw = ImageDraw.Draw(base)
        pill(draw, "TROIS MOMENTS • UN MÊME LOOK", (448, 514, 1016, 570), size=16)
    return base


def carousel_03(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    base = scene("sport-tennis.png", size, 0.30 if mobile else 0.50, 0.50)
    base.alpha_composite(bottom_gradient(size, 175))
    draw = ImageDraw.Draw(base)
    if mobile:
        subhead(draw, "ALLURE SPORTIVE", (34, 354), 16)
        headline(draw, "EN MOUVEMENT", (34, 382), 30)
    else:
        pill(draw, "ALLURE SPORTIVE • EN MOUVEMENT", (878, 504, 1396, 560), size=16)
    return base


def carousel_04(size: tuple[int, int]) -> Image.Image:
    source = Image.open(SCENES / "color-board-reference-layout.png")
    mobile = size == MOBILE
    if mobile:
        base = Image.new("RGBA", size, (248, 245, 238, 255))
        top = source.crop((0, 0, source.width, round(source.height * .59))).resize((600, 146), Image.Resampling.LANCZOS)
        base.alpha_composite(top.convert("RGBA"), (0, 0))
        draw = ImageDraw.Draw(base)
        headline(draw, "PLUSIEURS COLORIS", (300, 168), 30, INK, "ma")
        subhead(draw, "UN STYLE • PLUSIEURS POSSIBILITÉS", (300, 207), 13, DENIM, "ma")
        y0 = round(source.height * .64)
        columns = 5
        for i in range(columns):
            x0 = round(i * source.width / columns)
            x1 = round((i + 1) * source.width / columns)
            product = source.crop((x0, y0, x1, source.height))
            fitted = contain(product, (116, 190))
            base.alpha_composite(fitted, (i * 120 + (120 - fitted.width) // 2, 246 + (190 - fitted.height) // 2))
    else:
        base = cover(source, size, 0.50, 0.50).convert("RGBA")
        draw = ImageDraw.Draw(base)
        headline(draw, "PLUSIEURS COLORIS", (732, 350), 38, INK, "ma")
        subhead(draw, "UN STYLE • PLUSIEURS POSSIBILITÉS", (732, 389), 16, DENIM, "ma")
    return base


def summary(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    base = scene("hero-city.png", size, 0.30, 0.50).filter(ImageFilter.GaussianBlur(4)).convert("RGBA")
    base.alpha_composite(Image.new("RGBA", size, (245, 243, 238, 150)))
    draw = ImageDraw.Draw(base)
    if mobile:
        headline(draw, "DÉTAILS EN UN COUP D’ŒIL", (300, 18), 27, INK, "ma")
        paste_cutout(base, FLAT_CUTOUT, (145, 70, 455, 420))
        pill(draw, "REVERS", (18, 92, 180, 130), dark=True, size=12)
        pill(draw, "4 BOUTONS", (414, 150, 582, 188), dark=True, size=12)
        pill(draw, "2 POCHES", (18, 305, 190, 343), dark=True, size=12)
        pill(draw, "MANCHES LONGUES", (400, 362, 582, 400), dark=True, size=12)
    else:
        draw.rounded_rectangle((54, 42, 1410, 558), radius=34, fill=(246, 243, 237, 215))
        headline(draw, "DÉTAILS DU PRODUIT EN UN COUP D’ŒIL", (732, 60), 40, INK, "ma")
        paste_cutout(base, FLAT_CUTOUT, (512, 118, 952, 552))
        pill(draw, "COL À REVERS", (110, 180, 390, 230), dark=True, size=16)
        pill(draw, "QUATRE BOUTONS", (1074, 220, 1350, 270), dark=True, size=16)
        pill(draw, "DEUX POCHES AVANT", (90, 395, 410, 445), dark=True, size=16)
        pill(draw, "MANCHES LONGUES", (1080, 425, 1350, 475), dark=True, size=16)
    return base


def save(image: Image.Image, path: Path) -> None:
    image.convert("RGB").save(path, "JPEG", quality=91, optimize=True, progressive=True, dpi=(72, 72))


def overview(paths: list[Path], path: Path, width: int) -> None:
    images = [Image.open(p).convert("RGB") for p in paths]
    h = round(width * images[0].height / images[0].width)
    gap = 18
    canvas = Image.new("RGB", (width, gap + len(images) * (h + gap)), (23, 26, 29))
    y = gap
    for im in images:
        canvas.paste(im.resize((width, h), Image.Resampling.LANCZOS), (0, y))
        y += h + gap
    canvas.save(path, "JPEG", quality=87, optimize=True, progressive=True)


def main() -> None:
    jobs = [
        ("01_single_image_hero", module_01),
        ("02_single_image_silhouette", module_02),
        ("03_single_image_details", module_03),
        ("04_single_image_lifestyle", module_04),
        ("05_single_image_size_guide", module_05),
        ("06_carousel_01", carousel_01),
        ("06_carousel_02", carousel_02),
        ("06_carousel_03", carousel_03),
        ("06_carousel_04", carousel_04),
        ("07_single_image_summary", summary),
    ]
    desktops, mobiles = [], []
    for stem, builder in jobs:
        dp, mp = ROOT / f"{stem}_desktop.jpg", ROOT / f"{stem}_mobile.jpg"
        save(builder(DESKTOP), dp)
        save(builder(MOBILE), mp)
        desktops.append(dp)
        mobiles.append(mp)
    overview(desktops, ROOT / "_preview" / "00_overview_desktop_v3.jpg", 1171)
    overview(mobiles, ROOT / "_preview" / "00_overview_mobile_v3.jpg", 600)


if __name__ == "__main__":
    main()
