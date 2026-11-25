from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from scipy import ndimage


ROOT = Path(__file__).resolve().parent
SRC = ROOT.parent / "enjinia" / "sources"
BG = ROOT / "_generated-backgrounds"
SCENES = ROOT / "_generated-scenes-v2"

DESKTOP = (1464, 600)
MOBILE = (600, 450)

FONT_HEAD = Path(r"C:\Windows\Fonts\impact.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_SEMIBOLD = Path(r"C:\Windows\Fonts\seguisb.ttf")
FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")

OFF_WHITE = (242, 238, 229, 255)
BRONZE = (203, 145, 88, 255)
TEAL = (109, 169, 168, 255)
INK = (9, 13, 17, 255)


def font(size: int, kind: str = "regular") -> ImageFont.FreeTypeFont:
    path = {
        "head": FONT_HEAD,
        "bold": FONT_BOLD,
        "semibold": FONT_SEMIBOLD,
        "regular": FONT_REGULAR,
    }[kind]
    return ImageFont.truetype(str(path), size=size)


def cover(image: Image.Image, size: tuple[int, int], fx: float = 0.5, fy: float = 0.5) -> Image.Image:
    image = image.convert("RGB")
    scale = max(size[0] / image.width, size[1] / image.height)
    resized = image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)
    left = round((resized.width - size[0]) * fx)
    top = round((resized.height - size[1]) * fy)
    left = max(0, min(left, resized.width - size[0]))
    top = max(0, min(top, resized.height - size[1]))
    return resized.crop((left, top, left + size[0], top + size[1]))


def save(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, "PNG", optimize=True, dpi=(72, 72))


def darken(image: Image.Image, opacity: int = 75) -> Image.Image:
    base = image.convert("RGBA")
    base.alpha_composite(Image.new("RGBA", base.size, (5, 9, 13, opacity)))
    return base


def gradient(size: tuple[int, int], horizontal: bool = True, reverse: bool = False, alpha: int = 220) -> Image.Image:
    w, h = size
    if horizontal:
        strip = Image.new("RGBA", (w, 1))
        px = strip.load()
        for x in range(w):
            t = x / max(1, w - 1)
            if reverse:
                t = 1 - t
            px[x, 0] = (4, 8, 12, round(alpha * (1 - t)))
        return strip.resize((w, h), Image.Resampling.BILINEAR)
    strip = Image.new("RGBA", (1, h))
    px = strip.load()
    for y in range(h):
        t = y / max(1, h - 1)
        if reverse:
            t = 1 - t
        px[0, y] = (4, 8, 12, round(alpha * (1 - t)))
    return strip.resize((w, h), Image.Resampling.BILINEAR)


def bg(name: str, size: tuple[int, int], fx: float = 0.5, fy: float = 0.5) -> Image.Image:
    return cover(Image.open(BG / name), size, fx, fy).convert("RGBA")


def scene(name: str, size: tuple[int, int], fx: float = 0.5, fy: float = 0.5) -> Image.Image:
    variant = "mobile" if size == MOBILE else "desktop"
    return cover(Image.open(SCENES / f"{name}-{variant}-scene.png"), size, fx, fy).convert("RGBA")


SUBJECTS: dict[tuple[int, int], Image.Image] = {}


def extract_subject(path: Path) -> Image.Image:
    image = Image.open(path).convert("RGB")
    arr = np.asarray(image)
    rgb_min = arr.min(axis=2)
    rgb_max = arr.max(axis=2)
    white = (rgb_min > 220) & ((rgb_max - rgb_min) < 38)
    seed = np.zeros(white.shape, dtype=bool)
    seed[0, :] = white[0, :]
    seed[-1, :] = white[-1, :]
    seed[:, 0] = white[:, 0]
    seed[:, -1] = white[:, -1]
    background = ndimage.binary_propagation(seed, mask=white)
    alpha_arr = (~background).astype(np.uint8) * 255
    alpha_arr = ndimage.binary_fill_holes(alpha_arr > 0).astype(np.uint8) * 255
    alpha = Image.fromarray(alpha_arr, "L").filter(ImageFilter.GaussianBlur(0.75))
    result = image.convert("RGBA")
    result.putalpha(alpha)
    bbox = alpha.getbbox()
    return result.crop(bbox) if bbox else result


def subject(number: int, view: int = 2) -> Image.Image:
    key = (number, view)
    if key not in SUBJECTS:
        SUBJECTS[key] = extract_subject(SRC / f"product-{number:02d}-{view}.jpg")
    return SUBJECTS[key].copy()


def place_subject(base: Image.Image, item: Image.Image, cx: int, bottom: int, height: int, shadow: bool = True) -> None:
    ratio = height / item.height
    item = item.resize((round(item.width * ratio), height), Image.Resampling.LANCZOS)
    x = round(cx - item.width / 2)
    y = bottom - height
    if shadow:
        alpha = item.getchannel("A").filter(ImageFilter.GaussianBlur(max(6, height // 55)))
        layer = Image.new("RGBA", item.size, (0, 0, 0, 145))
        layer.putalpha(alpha.point(lambda a: round(a * 0.62)))
        base.alpha_composite(layer, (x + 12, y + 12))
    base.alpha_composite(item, (x, y))


def paste_panel(
    base: Image.Image,
    image: Image.Image,
    polygon: list[tuple[int, int]],
    fx: float = 0.5,
    fy: float = 0.5,
    tint: int = 20,
) -> None:
    x0 = min(x for x, _ in polygon)
    y0 = min(y for _, y in polygon)
    x1 = max(x for x, _ in polygon)
    y1 = max(y for _, y in polygon)
    panel = cover(image, (x1 - x0, y1 - y0), fx, fy).convert("RGBA")
    if tint:
        panel.alpha_composite(Image.new("RGBA", panel.size, (4, 8, 12, tint)))
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).polygon(polygon, fill=255)
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    layer.alpha_composite(panel, (x0, y0))
    layer.putalpha(mask)
    base.alpha_composite(layer)


def line(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], width: int = 3, color: tuple[int, int, int, int] = BRONZE) -> None:
    draw.line(xy, fill=color, width=width)


def centered_text(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], used_font: ImageFont.FreeTypeFont, fill=OFF_WHITE, stroke: int = 0) -> None:
    bbox = draw.textbbox((0, 0), text, font=used_font, stroke_width=stroke)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x0, y0, x1, y1 = box
    draw.text(((x0 + x1 - tw) / 2 - bbox[0], (y0 + y1 - th) / 2 - bbox[1]), text, font=used_font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 150))


def headline(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, size: int, fill=OFF_WHITE, anchor: str = "la") -> None:
    draw.text((x, y), text, font=font(size, "head"), fill=fill, stroke_width=max(1, size // 32), stroke_fill=(0, 0, 0, 175), anchor=anchor)


def subtitle(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, size: int, fill=BRONZE, anchor: str = "la") -> None:
    draw.text((x, y), text, font=font(size, "semibold"), fill=fill, anchor=anchor)


def floor_shadow(base: Image.Image, box: tuple[int, int, int, int], opacity: int = 115) -> None:
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse(box, fill=(0, 0, 0, opacity))
    base.alpha_composite(layer.filter(ImageFilter.GaussianBlur(18)))


def module_01(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    base = scene("01-hero", size)
    draw = ImageDraw.Draw(base)
    if mobile:
        base.alpha_composite(gradient((410, 450), horizontal=True, alpha=220), (0, 0))
        headline(draw, "VESTES BRODÉES", 42, 78, 45)
        headline(draw, "POUR HOMME", 42, 130, 39, fill=(226, 199, 166, 255))
        line(draw, (42, 188, 298, 188), 2)
        subtitle(draw, "HALLOWEEN • STYLE AFFIRMÉ", 42, 207, 16)
    else:
        base.alpha_composite(gradient((790, 600), horizontal=True, alpha=225), (0, 0))
        headline(draw, "VESTES BRODÉES", 82, 176, 62)
        headline(draw, "POUR HOMME", 82, 250, 56, fill=(226, 199, 166, 255))
        line(draw, (82, 329, 522, 329), 3)
        subtitle(draw, "HALLOWEEN • STYLE AFFIRMÉ", 82, 360, 22)
    return base


def module_02(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    base = scene("02-city", size)
    draw = ImageDraw.Draw(base)
    if mobile:
        base.alpha_composite(gradient((355, 450), horizontal=True, alpha=215), (0, 0))
        headline(draw, "STYLE URBAIN", 38, 68, 48)
        subtitle(draw, "UNE PRÉSENCE", 38, 126, 17)
        subtitle(draw, "QUI SE DÉMARQUE", 38, 151, 17)
        line(draw, (38, 191, 265, 191), 2)
    else:
        draw.rounded_rectangle((540, 102, 1090, 330), radius=16, fill=(5, 9, 13, 182), outline=(198, 142, 86, 155), width=2)
        headline(draw, "STYLE URBAIN", 815, 160, 64, anchor="ma")
        subtitle(draw, "UNE PRÉSENCE QUI SE DÉMARQUE", 815, 238, 23, anchor="ma")
        line(draw, (650, 286, 980, 286), 3)
    return base


def module_03(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    base = scene("03-lookbook", size)
    draw = ImageDraw.Draw(base)
    if mobile:
        draw.rounded_rectangle((145, 20, 455, 124), radius=12, fill=(5, 8, 12, 205), outline=(201, 150, 95, 150), width=2)
        headline(draw, "IDÉES DE LOOK", 300, 37, 39, anchor="ma")
        subtitle(draw, "3 SCÈNES • 3 ATTITUDES", 300, 83, 15, anchor="ma")
    else:
        draw.rounded_rectangle((485, 470, 979, 585), radius=14, fill=(5, 8, 12, 205), outline=(201, 150, 95, 150), width=2)
        headline(draw, "IDÉES DE LOOK", 732, 486, 49, anchor="ma")
        subtitle(draw, "3 SCÈNES • 3 ATTITUDES", 732, 544, 19, anchor="ma")
    return base


def detail_crop(number: int, box: tuple[int, int, int, int], size: tuple[int, int], fx: float = 0.5, fy: float = 0.5) -> Image.Image:
    image = Image.open(SRC / f"product-{number:02d}-2.jpg").convert("RGB").crop(box)
    return cover(image, size, fx, fy).convert("RGBA")


def detail_cell(base: Image.Image, image: Image.Image, box: tuple[int, int, int, int], label: str, label_size: int) -> None:
    x0, y0, x1, y1 = box
    cell = cover(image, (x1 - x0, y1 - y0), 0.5, 0.5).convert("RGBA")
    cell.alpha_composite(gradient(cell.size, horizontal=False, reverse=False, alpha=185))
    base.alpha_composite(cell, (x0, y0))
    draw = ImageDraw.Draw(base)
    draw.rectangle(box, outline=(189, 132, 79, 255), width=3)
    centered_text(draw, label, (x0, y1 - 48, x1, y1 - 5), font(label_size, "bold"), OFF_WHITE)


def module_04(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    base = darken(bg("atelier.png", size, 0.50, 0.48), 75)
    draw = ImageDraw.Draw(base)
    if mobile:
        headline(draw, "DÉTAILS DU PRODUIT", 300, 25, 42, anchor="ma")
        line(draw, (96, 80, 504, 80), 2)
        detail_cell(base, detail_crop(2, (360, 45, 1240, 860), (300, 175)), (0, 94, 300, 270), "VELOURS CÔTELÉ", 15)
        detail_cell(base, detail_crop(1, (140, 300, 1120, 1270), (300, 175)), (300, 94, 600, 270), "BRODERIES", 15)
        detail_cell(base, detail_crop(7, (280, 80, 1320, 1120), (300, 180)), (0, 270, 300, 450), "REVERS TAILLÉ", 15)
        duo = Image.new("RGBA", (300, 180), (18, 22, 26, 255))
        place_subject(duo, subject(2, 2), 82, 187, 170, shadow=False)
        place_subject(duo, subject(2, 3), 220, 187, 165, shadow=False)
        detail_cell(base, duo, (300, 270, 600, 450), "AVANT & DOS", 15)
    else:
        left = Image.new("RGBA", (625, 600), (11, 15, 19, 255))
        left.alpha_composite(cover(Image.open(BG / "atelier.png"), (625, 600), 0.33, 0.50).convert("RGBA"))
        left.alpha_composite(Image.new("RGBA", left.size, (4, 8, 12, 55)))
        floor_shadow(left, (25, 500, 600, 650), 120)
        place_subject(left, subject(1), 316, 624, 560)
        base.alpha_composite(left, (0, 0))
        draw.rectangle((8, 8, 618, 592), outline=(189, 132, 79, 255), width=3)
        headline(draw, "DÉTAILS DU PRODUIT", 1042, 20, 48, anchor="ma")
        line(draw, (700, 73, 1385, 73), 2)
        detail_cell(base, detail_crop(2, (360, 45, 1240, 860), (405, 245)), (635, 85, 1045, 335), "VELOURS CÔTELÉ", 20)
        detail_cell(base, detail_crop(1, (140, 300, 1120, 1270), (410, 245)), (1045, 85, 1456, 335), "BRODERIES", 20)
        detail_cell(base, detail_crop(7, (280, 80, 1320, 1120), (405, 255)), (635, 335, 1045, 592), "REVERS TAILLÉ", 20)
        duo = Image.new("RGBA", (411, 257), (18, 22, 26, 255))
        place_subject(duo, subject(2, 2), 113, 270, 240, shadow=False)
        place_subject(duo, subject(2, 3), 302, 270, 232, shadow=False)
        detail_cell(base, duo, (1045, 335, 1456, 592), "AVANT & DOS", 20)
    return base


CAROUSEL_TABS = ["FLORAL DORÉ", "DÍA DE MUERTOS", "HALLOWEEN", "NOËL"]
CAROUSEL_CONFIG = [
    ("atelier.png", [2, 3, 4], "FLORAL DORÉ", "ÉLÉGANCE ORNEMENTALE", (0.49, 0.50)),
    ("atelier.png", [1, 4, 5], "DÍA DE MUERTOS", "COULEURS & CARACTÈRE", (0.50, 0.50)),
    ("city-night.png", [7, 8, 9], "HALLOWEEN", "MOTIFS SAISONNIERS", (0.52, 0.54)),
    ("lounge-studio.png", [10, 11], "NOËL", "ESPRIT FESTIF", (0.48, 0.48)),
]


def carousel_slide(index: int, size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    background_name, products, title, sub, focus = CAROUSEL_CONFIG[index]
    base = darken(bg(background_name, size, *focus), 45)
    draw = ImageDraw.Draw(base)
    if mobile:
        draw.rectangle((0, 0, 600, 104), fill=(8, 12, 16, 238))
        positions = [(8, 12, 292, 48), (308, 12, 592, 48), (8, 57, 292, 93), (308, 57, 592, 93)]
        for tab_index, (tab, box) in enumerate(zip(CAROUSEL_TABS, positions)):
            fill = (200, 143, 85, 255) if tab_index == index else (25, 31, 36, 255)
            text_fill = (16, 20, 24, 255) if tab_index == index else (192, 190, 184, 255)
            draw.rounded_rectangle(box, radius=7, fill=fill, outline=(91, 97, 101, 255), width=1)
            centered_text(draw, tab, box, font(13, "bold"), text_fill)
        floor_shadow(base, (45, 360, 595, 490), 120)
        if len(products) == 2:
            xs, hs = [205, 430], [325, 345]
        elif len(products) == 3:
            xs, hs = [120, 300, 485], [280, 330, 280]
        else:
            xs, hs = [80, 225, 380, 530], [245, 285, 300, 250]
        for number, x, h in zip(products, xs, hs):
            place_subject(base, subject(number), x, 472, h)
        draw.rounded_rectangle((44, 338, 556, 432), radius=9, fill=(6, 10, 14, 190), outline=(203, 145, 88, 180), width=2)
        headline(draw, title, 300, 350, 34, anchor="ma")
        subtitle(draw, sub, 300, 393, 14, anchor="ma")
    else:
        nav_w = 190
        draw.rectangle((0, 0, nav_w, 600), fill=(7, 11, 15, 240))
        for tab_index, tab in enumerate(CAROUSEL_TABS):
            y0 = 100 + tab_index * 90
            if tab_index == index:
                draw.rectangle((0, y0, nav_w, y0 + 70), fill=(205, 146, 86, 255))
                fill = (17, 21, 24, 255)
            else:
                draw.rectangle((18, y0 + 69, nav_w - 18, y0 + 70), fill=(86, 92, 96, 170))
                fill = (184, 184, 180, 255)
            centered_text(draw, tab, (10, y0, nav_w - 10, y0 + 70), font(16, "bold"), fill)
        draw.rounded_rectangle((235, 52, 750, 178), radius=8, fill=(7, 11, 15, 178))
        headline(draw, title, 270, 67, 52)
        subtitle(draw, sub, 270, 131, 20)
        line(draw, (270, 165, 660, 165), 2)
        floor_shadow(base, (490, 490, 1460, 660), 130)
        if len(products) == 2:
            xs, hs = [960, 1280], [530, 565]
        elif len(products) == 3:
            xs, hs = [780, 1080, 1360], [455, 540, 460]
        else:
            xs, hs = [650, 890, 1135, 1390], [410, 470, 515, 420]
        for number, x, h in zip(products, xs, hs):
            place_subject(base, subject(number), x, 630, h)
    return base


SIZE_ROWS = [
    ("S", "108 cm / 42.52 in", "45 cm / 17.72 in", "63.5 cm / 25.00 in", "74 cm / 29.13 in"),
    ("M", "113 cm / 44.49 in", "46.5 cm / 18.31 in", "64.2 cm / 25.28 in", "75 cm / 29.53 in"),
    ("L", "118 cm / 46.46 in", "48 cm / 18.90 in", "64.9 cm / 25.55 in", "76 cm / 29.92 in"),
    ("XL", "123 cm / 48.43 in", "49.5 cm / 19.49 in", "65.6 cm / 25.83 in", "77 cm / 30.31 in"),
    ("XXL", "128 cm / 50.39 in", "51 cm / 20.08 in", "66.3 cm / 26.10 in", "78 cm / 30.71 in"),
    ("XXXL", "133 cm / 52.36 in", "52.5 cm / 20.67 in", "67 cm / 26.38 in", "79 cm / 31.10 in"),
    ("XXXXL", "138 cm / 54.33 in", "54 cm / 21.26 in", "67.7 cm / 26.65 in", "80 cm / 31.50 in"),
]


def size_table(base: Image.Image, box: tuple[int, int, int, int], mobile: bool) -> None:
    draw = ImageDraw.Draw(base)
    x0, y0, x1, y1 = box
    rows = len(SIZE_ROWS) + 1
    row_h = (y1 - y0) / rows
    fractions = [0.12, 0.22, 0.22, 0.22, 0.22]
    xs = [x0]
    for f in fractions:
        xs.append(xs[-1] + round((x1 - x0) * f))
    headers = ["Taille", "Poitrine", "Épaules", "Manche", "Longueur"]
    for r in range(rows):
        ya = round(y0 + r * row_h)
        yb = round(y0 + (r + 1) * row_h)
        fill = (21, 34, 37, 244) if r == 0 else ((18, 23, 27, 235) if r % 2 else (30, 36, 40, 235))
        draw.rectangle((x0, ya, x1, yb), fill=fill)
    for x in xs:
        draw.line((x, y0, x, y1), fill=(181, 130, 82, 255), width=2 if not mobile else 1)
    for r in range(rows + 1):
        y = round(y0 + r * row_h)
        draw.line((x0, y, x1, y), fill=(181, 130, 82, 255), width=2 if not mobile else 1)
    head_font = font(17 if not mobile else 11, "bold")
    body_font = font(14 if not mobile else 9, "semibold")
    for c, value in enumerate(headers):
        centered_text(draw, value, (xs[c], y0, xs[c + 1], round(y0 + row_h)), head_font, OFF_WHITE)
    for r, row in enumerate(SIZE_ROWS, 1):
        for c, value in enumerate(row):
            centered_text(draw, value, (xs[c], round(y0 + r * row_h), xs[c + 1], round(y0 + (r + 1) * row_h)), body_font, (233, 230, 223, 255))


def module_06(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    base = darken(bg("atelier.png", size, 0.42, 0.48), 80)
    draw = ImageDraw.Draw(base)
    if mobile:
        headline(draw, "GUIDE DES TAILLES", 300, 18, 40, anchor="ma")
        subtitle(draw, "MESURES DU VÊTEMENT", 300, 60, 14, anchor="ma")
        line(draw, (100, 87, 500, 87), 2)
        size_table(base, (14, 104, 586, 434), True)
    else:
        headline(draw, "GUIDE DES TAILLES", 505, 28, 63, anchor="ma")
        subtitle(draw, "MESURES DU VÊTEMENT", 505, 94, 22, anchor="ma")
        line(draw, (140, 132, 870, 132), 2)
        size_table(base, (30, 160, 1010, 560), False)
        floor_shadow(base, (1000, 500, 1465, 650), 120)
        place_subject(base, subject(2), 1240, 625, 560)
    return base


def module_07(size: tuple[int, int]) -> Image.Image:
    mobile = size == MOBILE
    base = darken(bg("lounge-studio.png", size, 0.50, 0.50), 30)
    draw = ImageDraw.Draw(base)
    products = [2, 1, 5, 8, 11]
    if mobile:
        boxes = [(0, 0, 200, 235), (200, 0, 400, 235), (400, 0, 600, 235), (0, 235, 300, 450), (300, 235, 600, 450)]
        for n, box in zip(products, boxes):
            x0, y0, x1, y1 = box
            panel = cover(Image.open(SRC / f"product-{n:02d}-1.jpg"), (x1 - x0, y1 - y0), 0.5, 0.5).convert("RGBA")
            panel.alpha_composite(Image.new("RGBA", panel.size, (3, 7, 10, 20)))
            base.alpha_composite(panel, (x0, y0))
            draw.rectangle(box, outline=(214, 158, 100, 255), width=2)
        draw.rounded_rectangle((70, 170, 530, 325), radius=9, fill=(7, 11, 15, 220), outline=(203, 145, 88, 210), width=2)
        headline(draw, "AFFIRMEZ", 300, 191, 48, anchor="ma")
        headline(draw, "VOTRE STYLE", 300, 241, 44, fill=(226, 199, 166, 255), anchor="ma")
        subtitle(draw, "VILLE • SOIRÉE • SAISON FESTIVE", 300, 289, 14, anchor="ma")
    else:
        bounds = [(0, 0, 305, 600), (285, 0, 600, 600), (580, 0, 890, 600), (870, 0, 1175, 600), (1155, 0, 1464, 600)]
        shifts = [-40, -20, 0, 20, 40]
        for n, box, shift in zip(products, bounds, shifts):
            x0, y0, x1, y1 = box
            poly = [(x0 + max(0, shift), 0), (x1 + min(0, shift), 0), (x1 - max(0, shift), 600), (x0 - min(0, shift), 600)]
            paste_panel(base, Image.open(SRC / f"product-{n:02d}-1.jpg"), poly, 0.5, 0.5, 8)
            draw.line((poly[1][0], poly[1][1], poly[2][0], poly[2][1]), fill=(230, 191, 143, 255), width=3)
        draw.polygon([(315, 410), (1148, 410), (1080, 600), (365, 600)], fill=(6, 10, 14, 226))
        headline(draw, "AFFIRMEZ VOTRE STYLE", 730, 440, 60, anchor="ma")
        line(draw, (470, 512, 990, 512), 3)
        subtitle(draw, "VILLE • SOIRÉE • SAISON FESTIVE", 730, 548, 21, anchor="ma")
    return base


def overview(paths: Iterable[Path], output: Path, label: str, width: int) -> None:
    images = [Image.open(path).convert("RGB") for path in paths]
    thumb_h = round(width * images[0].height / images[0].width)
    label_h = 42
    canvas = Image.new("RGB", (width, len(images) * (thumb_h + label_h)), (20, 24, 28))
    draw = ImageDraw.Draw(canvas)
    y = 0
    for i, image in enumerate(images, 1):
        shown = image.resize((width, thumb_h), Image.Resampling.LANCZOS)
        canvas.paste(shown, (0, y))
        y += thumb_h
        draw.rectangle((0, y, width, y + label_h), fill=(18, 23, 28))
        draw.text((18, y + 9), f"{label} {i:02d}", font=font(17, "semibold"), fill=(238, 233, 224))
        y += label_h
    save(canvas, output)


def main() -> None:
    paths_desktop: list[Path] = []
    paths_mobile: list[Path] = []
    modules = [module_01, module_02, module_03, module_04]
    names = ["01-hero", "02-style-urbain", "03-idees-look", "04-details-produit"]
    for builder, name in zip(modules, names):
        dp = ROOT / name / f"{name}-desktop-1464x600.png"
        mp = ROOT / name / f"{name}-mobile-600x450.png"
        save(builder(DESKTOP), dp)
        save(builder(MOBILE), mp)
        paths_desktop.append(dp)
        paths_mobile.append(mp)

    carousel_dir = ROOT / "05-carousel-collections"
    for i in range(4):
        slug = CAROUSEL_TABS[i].lower().replace(' ', '-').replace('é', 'e').replace('í', 'i').replace('ë', 'e')
        dp = carousel_dir / f"05-{i + 1:02d}-{slug}-desktop-1464x600.png"
        mp = carousel_dir / f"05-{i + 1:02d}-{slug}-mobile-600x450.png"
        save(carousel_slide(i, DESKTOP), dp)
        save(carousel_slide(i, MOBILE), mp)
    paths_desktop.append(carousel_dir / "05-01-floral-dore-desktop-1464x600.png")
    paths_mobile.append(carousel_dir / "05-01-floral-dore-mobile-600x450.png")

    dp = ROOT / "06-guide-tailles" / "06-guide-tailles-desktop-1464x600.png"
    mp = ROOT / "06-guide-tailles" / "06-guide-tailles-mobile-600x450.png"
    save(module_06(DESKTOP), dp)
    save(module_06(MOBILE), mp)
    paths_desktop.append(dp)
    paths_mobile.append(mp)

    dp = ROOT / "07-affirmez-style" / "07-affirmez-style-desktop-1464x600.png"
    mp = ROOT / "07-affirmez-style" / "07-affirmez-style-mobile-600x450.png"
    save(module_07(DESKTOP), dp)
    save(module_07(MOBILE), mp)
    paths_desktop.append(dp)
    paths_mobile.append(mp)

    overview(paths_desktop, ROOT / "00-apercu-desktop.png", "BUREAU", 1171)
    overview(paths_mobile, ROOT / "00-apercu-mobile.png", "MOBILE", 600)


if __name__ == "__main__":
    main()
