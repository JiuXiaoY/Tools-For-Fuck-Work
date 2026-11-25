from __future__ import annotations

from pathlib import Path
import csv
import math
import random
import textwrap

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parent
GEN = ROOT / "_generated_l89"
SRC = ROOT / "sources"
DESKTOP = ROOT / "desktop"
MOBILE = ROOT / "mobile_600x450"
PREVIEW = ROOT / "_preview"

WIDE = (1464, 600)
PHONE = (600, 450)

FONT_FUN = Path(r"C:\Windows\Fonts\JOKERMAN.TTF")
FONT_DISPLAY = Path(r"C:\Windows\Fonts\impact.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\arialbd.ttf")
FONT_BODY = Path(r"C:\Windows\Fonts\arial.ttf")

IVORY = (247, 239, 220)
AMBER = (244, 150, 45)
COPPER = (189, 92, 46)
TEAL = (82, 205, 193)
VIOLET = (196, 91, 240)
INK = (12, 13, 18)


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def cover(img: Image.Image, size: tuple[int, int], focus=(0.5, 0.5)) -> Image.Image:
    img = img.convert("RGB")
    sw, sh = img.size
    tw, th = size
    scale = max(tw / sw, th / sh)
    nw, nh = int(math.ceil(sw * scale)), int(math.ceil(sh * scale))
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    fx, fy = focus
    left = int((nw - tw) * fx)
    top = int((nh - th) * fy)
    left = max(0, min(left, nw - tw))
    top = max(0, min(top, nh - th))
    return resized.crop((left, top, left + tw, top + th))


def gradient_overlay(im: Image.Image, side: str, strength: int = 215, span: float = 0.62, color=INK) -> None:
    w, h = im.size
    alpha = Image.new("L", (w, h), 0)
    px = alpha.load()
    if side in {"left", "right"}:
        limit = max(1, int(w * span))
        for x in range(w):
            d = x if side == "left" else w - 1 - x
            a = int(strength * max(0.0, 1.0 - d / limit) ** 1.8)
            for y in range(h):
                px[x, y] = a
    else:
        limit = max(1, int(h * span))
        for y in range(h):
            d = y if side == "top" else h - 1 - y
            a = int(strength * max(0.0, 1.0 - d / limit) ** 1.8)
            for x in range(w):
                px[x, y] = a
    layer = Image.new("RGBA", (w, h), (*color[:3], 0))
    layer.putalpha(alpha)
    im.alpha_composite(layer)


def vignette(im: Image.Image, strength: int = 120) -> None:
    w, h = im.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    for i in range(48):
        a = int(strength * (1 - i / 48) ** 2)
        d.rounded_rectangle((i * 3, i * 2, w - i * 3, h - i * 2), radius=36, outline=a, width=8)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    layer.putalpha(mask.filter(ImageFilter.GaussianBlur(20)))
    im.alpha_composite(layer)


def pill(draw: ImageDraw.ImageDraw, xy, label: str, accent=AMBER, scale=1.0):
    x, y = xy
    f = font(FONT_BOLD, int(18 * scale))
    box = draw.textbbox((0, 0), label, font=f)
    width = box[2] - box[0] + int(34 * scale)
    height = int(38 * scale)
    draw.rounded_rectangle((x, y, x + width, y + height), radius=height // 2,
                           fill=(10, 10, 15, 185), outline=(*accent, 235), width=max(1, int(2 * scale)))
    draw.text((x + int(17 * scale), y + int(8 * scale)), label, font=f, fill=IVORY)
    return width


def draw_skull(draw: ImageDraw.ImageDraw, center, scale=1.0, fill=IVORY, accent=AMBER):
    cx, cy = center
    r = int(14 * scale)
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill)
    draw.rectangle((cx - int(8 * scale), cy + int(5 * scale), cx + int(8 * scale), cy + int(16 * scale)), fill=fill)
    e = int(4 * scale)
    draw.ellipse((cx - int(8 * scale), cy - int(3 * scale), cx - int(8 * scale) + e * 2, cy - int(3 * scale) + e * 2), fill=INK)
    draw.ellipse((cx + int(2 * scale), cy - int(3 * scale), cx + int(2 * scale) + e * 2, cy - int(3 * scale) + e * 2), fill=INK)
    draw.polygon([(cx, cy + int(4 * scale)), (cx - int(3 * scale), cy + int(9 * scale)), (cx + int(3 * scale), cy + int(9 * scale))], fill=accent)
    for dx in (-6, 0, 6):
        draw.line((cx + int(dx * scale), cy + int(9 * scale), cx + int(dx * scale), cy + int(16 * scale)), fill=INK, width=max(1, int(scale)))


def draw_title(draw, xy, text, size, max_width, fun=True, fill=IVORY, accent=AMBER,
               spacing=4, stroke=4, anchor="la", underline=False):
    path = FONT_FUN if fun else FONT_DISPLAY
    words = text.split()
    lines = []
    current = ""
    f = font(path, size)
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=f, stroke_width=stroke)[2] <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    line_h = int(size * 1.06)
    for i, line in enumerate(lines):
        shadow_xy = (x + 4, y + i * (line_h + spacing) + 6)
        draw.text(shadow_xy, line, font=f, fill=(0, 0, 0, 170), stroke_width=stroke + 2,
                  stroke_fill=(0, 0, 0, 150), anchor=anchor)
        draw.text((x, y + i * (line_h + spacing)), line, font=f, fill=fill,
                  stroke_width=stroke, stroke_fill=(30, 17, 17), anchor=anchor)
    underline_y = y + len(lines) * (line_h + spacing) + 7
    if underline and anchor == "la":
        draw.rounded_rectangle((x, underline_y, x + min(max_width, int(size * 3.25)), underline_y + 6), radius=3, fill=accent)
    return underline_y + 18


def draw_body(draw, xy, text, size, max_width, fill=(235, 232, 225), line_gap=7):
    f = font(FONT_BODY, size)
    words = text.split()
    lines, current = [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if draw.textbbox((0, 0), trial, font=f)[2] <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=f, fill=fill, stroke_width=1, stroke_fill=(0, 0, 0, 120))
        y += size + line_gap
    return y


def scene(name: str) -> Image.Image:
    path = Path(name)
    l89_name = f"{path.stem}-l89{path.suffix}"
    return Image.open(GEN / l89_name).convert("RGB")


def save_jpg(im: Image.Image, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.convert("RGB").save(path, quality=94, subsampling=0, optimize=True)


def module_hero(size, mobile=False):
    focus = (0.43, 0.5) if mobile else (0.5, 0.06)
    im = cover(scene("scene-01-castle-stride.png"), size, focus).convert("RGBA")
    gradient_overlay(im, "left", 225 if not mobile else 205, 0.60 if not mobile else 0.74)
    gradient_overlay(im, "bottom", 115, 0.35)
    vignette(im, 80)
    d = ImageDraw.Draw(im, "RGBA")
    if mobile:
        draw_body(d, (31, 46), "Une silhouette mystique pensée pour faire de chaque entrée une scène.", 20, 330)
        draw_title(d, (30, 132), "HALLOWEEN", 45, 340, True, spacing=0, stroke=3, underline=False)
        d.text((33, 193), "TENUE DE FÊTE", font=font(FONT_FUN, 25), fill=AMBER,
               stroke_width=2, stroke_fill=(28, 14, 15))
        pill(d, (30, 380), "HALLOWEEN  •  FESTIVAL  •  NUIT", scale=0.70)
    else:
        draw_skull(d, (84, 72), 1.15)
        draw_body(d, (72, 128), "Une silhouette d'assassin, une capuche sculpturale et une présence qui transforme la nuit.", 26, 590)
        draw_title(d, (70, 248), "HALLOWEEN", 70, 610, True, spacing=0, stroke=5, underline=False)
        d.text((75, 344), "TENUE DE FÊTE", font=font(FONT_FUN, 34), fill=AMBER,
               stroke_width=3, stroke_fill=(28, 14, 15))
        pill(d, (72, 475), "HALLOWEEN  •  FESTIVAL  •  NUIT", scale=1.0)
    return im


def product_cutout() -> Image.Image:
    raw = Image.open(SRC / "product-front-khaki.jpg").convert("RGBA")
    gray = ImageOps.grayscale(raw)
    inv = ImageOps.invert(gray)
    alpha = inv.point(lambda p: 0 if p < 8 else min(255, p * 8))
    raw.putalpha(alpha)
    return raw


def textured_back(size):
    w, h = size
    random.seed(73)
    im = Image.new("RGB", size, (17, 19, 24))
    px = im.load()
    for y in range(h):
        for x in range(w):
            t = x / max(1, w - 1)
            u = y / max(1, h - 1)
            glow = max(0, 1 - math.hypot(t - 0.58, u - 0.46) * 1.5)
            noise = random.randint(-5, 5)
            px[x, y] = (int(13 + 35 * glow + noise), int(15 + 25 * glow + noise), int(20 + 18 * glow + noise))
    return im.filter(ImageFilter.GaussianBlur(0.6)).convert("RGBA")


def module_design(size, mobile=False):
    im = textured_back(size)
    w, h = size
    d = ImageDraw.Draw(im, "RGBA")
    # Atmospheric rune wheel and copper arcs.
    cx, cy = (int(w * 0.56), int(h * 0.55))
    for r, a in ((210, 48), (165, 75), (118, 95)):
        rr = int(r * (h / 600))
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), outline=(*COPPER, a), width=max(1, int(2 * h / 600)))
    for k in range(8):
        ang = k * math.pi / 4
        d.line((cx, cy, cx + math.cos(ang) * int(h * 0.37), cy + math.sin(ang) * int(h * 0.37)), fill=(*COPPER, 55), width=2)
    cut = product_cutout()
    if mobile:
        cut.thumbnail((545, 330), Image.Resampling.LANCZOS)
        im.alpha_composite(cut, (int((w - cut.width) / 2), 60))
        labels = [
            (32, 355, "CAPUCHE ENVELOPPANTE"),
            (306, 355, "IMPRESSION DOS XXL"),
            (32, 404, "LONGUEUR L : 89 CM"),
            (306, 404, "SYMBOLE NORDIQUE"),
        ]
        for x, yy, label in labels:
            d.rounded_rectangle((x, yy, x + 258, yy + 34), radius=10, fill=(10, 11, 15, 215), outline=(*AMBER, 175), width=1)
            d.text((x + 11, yy + 9), label, font=font(FONT_BOLD, 13), fill=IVORY)
    else:
        cut.thumbnail((735, 535), Image.Resampling.LANCZOS)
        im.alpha_composite(cut, (690, 48))
        draw_skull(d, (78, 69), 1.0)
        draw_body(d, (68, 128), "Une coupe longue pensée pour le mouvement, relevée par deux signatures graphiques fortes.", 24, 545)
        draw_title(d, (68, 247), "LOOK DE FESTIVAL", 48, 560, True, spacing=0, stroke=4, underline=False)
        callouts = [
            (72, 365, "01", "CAPUCHE ENVELOPPANTE"),
            (72, 426, "02", "LONGUEUR L : 89 CM"),
            (72, 487, "03", "SYMBOLE NORDIQUE + DOS XXL"),
        ]
        for x, yy, num, label in callouts:
            d.ellipse((x, yy, x + 38, yy + 38), fill=(*AMBER, 235))
            d.text((x + 19, yy + 19), num, font=font(FONT_BOLD, 16), fill=INK, anchor="mm")
            d.text((x + 54, yy + 7), label, font=font(FONT_BOLD, 21), fill=IVORY)
    return im


def diagonal_triptych(size, mobile=False):
    w, h = size
    # The much narrower phone columns need their own subject-centred focal points.
    focal_x = (0.75, 0.19, 0.23) if mobile else (0.79, 0.15, 0.15)
    shot_specs = [
        # Focus values are aligned to the centre of each model, not to the scenery.
        # This keeps the complete hoodie body inside every third instead of cutting it
        # at the old diagonal overlap boundaries.
        ("scene-02-nordic-cliff-turn.png", (focal_x[0], 0.5)),
        ("scene-03-lantern-alley.png", (focal_x[1], 0.5)),
        ("scene-05-gothic-library.png", (focal_x[2], 0.5)),
    ]
    im = Image.new("RGBA", size, INK + (255,))
    edges = [0, int(w / 3), int(2 * w / 3), w]
    for i, (shot_name, focus) in enumerate(shot_specs):
        left, right = edges[i], edges[i + 1]
        shot = cover(scene(shot_name), (right - left, h), focus)
        im.paste(shot, (left, 0))
    d = ImageDraw.Draw(im, "RGBA")
    divider_w = 3 if not mobile else 2
    for x in edges[1:-1]:
        d.line((x, 0, x, h), fill=(244, 150, 45, 150), width=divider_w)
    gradient_overlay(im, "top", 205 if mobile else 180, 0.34)
    gradient_overlay(im, "bottom", 185, 0.32)
    if mobile:
        labels = [(100, "NORD"), (300, "LANTERNES"), (500, "GOTHIQUE")]
        for x, label in labels:
            d.text((x, 409), label, font=font(FONT_BOLD, 15), fill=IVORY, anchor="mm", stroke_width=2, stroke_fill=INK)
    else:
        labels = [(244, "LÉGENDE DU NORD"), (732, "NUIT DES LANTERNES"), (1220, "MYSTÈRE GOTHIQUE")]
        for x, label in labels:
            d.rounded_rectangle((x - 170, 528, x + 170, 573), radius=21, fill=(9, 10, 14, 205), outline=(*AMBER, 160), width=2)
            d.text((x, 551), label, font=font(FONT_BOLD, 19), fill=IVORY, anchor="mm")
    return im


CAROUSEL = [
    ("scene-01-castle-stride.png", (0.46, 0.06), "LA PORTE DES OMBRES", "Avancez. Le décor suivra.", "left", AMBER),
    ("scene-02-nordic-cliff-turn.png", (0.61, 0.06), "L'APPEL DU NORD", "Le dos imprimé prend toute la scène.", "left", (225, 115, 70)),
    ("scene-03-lantern-alley.png", (0.34, 0.06), "SOUS LES LANTERNES", "Une silhouette qui traverse les époques.", "right", (235, 72, 54)),
    ("scene-06-enchanted-forest.png", (0.37, 0.06), "LE SENTIER APRÈS MINUIT", "Libérez le mouvement.", "right", TEAL),
]


def carousel_panel(index: int, size, mobile=False):
    name, focus, title, subtitle, side, accent = CAROUSEL[index]
    im = cover(scene(name), size, focus).convert("RGBA")
    # On mobile, reserve top and bottom contrast while retaining the full action.
    gradient_overlay(im, side, 215, 0.56 if not mobile else 0.74)
    gradient_overlay(im, "bottom", 115, 0.32)
    d = ImageDraw.Draw(im, "RGBA")
    if mobile:
        x = 28 if side == "left" else 572
        anchor = "la" if side == "left" else "ra"
        draw_title(d, (x, 35), title, 34 if len(title) < 22 else 29, 430, True, spacing=0, stroke=3,
                   anchor=anchor, underline=False)
        d.text((x, 377), subtitle, font=font(FONT_BOLD, 18), fill=IVORY, anchor=anchor, stroke_width=2, stroke_fill=INK)
        d.text((x, 410), f"0{index + 1} / 04", font=font(FONT_BOLD, 14), fill=accent, anchor=anchor)
    else:
        x = 70 if side == "left" else size[0] - 70
        anchor = "la" if side == "left" else "ra"
        y = draw_title(d, (x, 170), title, 62 if len(title) < 22 else 52, 620, True, spacing=0, stroke=4,
                       anchor=anchor, underline=False)
        d.text((x, y + 22), subtitle, font=font(FONT_BOLD, 26), fill=IVORY, anchor=anchor, stroke_width=2, stroke_fill=INK)
        d.text((x, 510), f"0{index + 1} / 04", font=font(FONT_BOLD, 18), fill=accent, anchor=anchor)
    return im


def module_comfort(size, mobile=False):
    im = cover(scene("scene-05-gothic-library.png"), size, (0.37, 0.06)).convert("RGBA")
    gradient_overlay(im, "right", 228, 0.63 if not mobile else 0.78)
    gradient_overlay(im, "bottom", 105, 0.32)
    d = ImageDraw.Draw(im, "RGBA")
    if mobile:
        draw_title(d, (572, 30), "NUIT COSTUMÉE", 35, 390, True, spacing=0, stroke=3,
                   anchor="ra", underline=False)
        chips = [(34, 347, "TOUCHER DOUX"), (221, 347, "TISSU RESPIRANT"), (408, 347, "MATIÈRE TISSÉE")]
        for x, yy, label in chips:
            d.rounded_rectangle((x, yy, x + 158, yy + 64), radius=14, fill=(10, 10, 14, 210), outline=(*AMBER, 160), width=2)
            d.text((x + 79, yy + 32), label, font=font(FONT_BOLD, 13), fill=IVORY, anchor="mm")
    else:
        draw_body(d, (815, 125), "Confort simple, sensation souple et tissu respirant pour accompagner vos soirées d'automne et d'hiver.", 24, 540)
        draw_title(d, (1392, 265), "NUIT COSTUMÉE", 54, 580, True, spacing=0, stroke=4,
                   anchor="ra", underline=False)
        chips = [(815, 408, "TOUCHER\nDOUX"), (1010, 408, "TISSU\nRESPIRANT"), (1205, 408, "MATIÈRE\nTISSÉE")]
        for x, yy, label in chips:
            d.ellipse((x, yy, x + 145, yy + 145), fill=(10, 10, 14, 205), outline=(*AMBER, 185), width=3)
            d.text((x + 72, yy + 72), label, font=font(FONT_BOLD, 18), fill=IVORY, anchor="mm", align="center")
    return im


def module_fit(size, mobile=False):
    im = cover(scene("scene-04-halloween-festival.png"), size, (0.5, 0.05)).convert("RGBA")
    gradient_overlay(im, "top", 188, 0.34)
    gradient_overlay(im, "bottom", 202, 0.35)
    d = ImageDraw.Draw(im, "RGBA")
    if mobile:
        draw_title(d, (300, 24), "PRÊT POUR LA FÊTE", 29, 540, True, spacing=0, stroke=3,
                   anchor="ma", underline=False)
        labels = ["COUPE SLIM STANDARD", "AUTOMNE / HIVER", "LAVABLE EN MACHINE"]
        widths = [176, 153, 175]
        x = 32
        for label, ww in zip(labels, widths):
            d.rounded_rectangle((x, 383, x + ww, 421), radius=17, fill=(9, 10, 14, 215), outline=(*VIOLET, 170), width=2)
            d.text((x + ww / 2, 402), label, font=font(FONT_BOLD, 12), fill=IVORY, anchor="mm")
            x += ww + 10
    else:
        draw_title(d, (732, 34), "PRÊT POUR LA FÊTE", 52, 1250, True, spacing=0, stroke=4,
                   anchor="ma", underline=False)
        labels = ["COUPE SLIM STANDARD", "AUTOMNE / HIVER", "LAVABLE EN MACHINE"]
        x = 296
        for label in labels:
            ww = 280
            d.rounded_rectangle((x, 510, x + ww, 558), radius=22, fill=(9, 10, 14, 218), outline=(*VIOLET, 175), width=2)
            d.text((x + ww / 2, 534), label, font=font(FONT_BOLD, 18), fill=IVORY, anchor="mm")
            x += ww + 16
    return im


SIZE_DATA = [
    ("S", "106 cm / 41,73\"", "50 cm / 19,69\"", "62 cm / 24,41\"", "84 cm / 33,07\""),
    ("M", "112 cm / 44,09\"", "52 cm / 20,47\"", "63 cm / 24,80\"", "87 cm / 34,25\""),
    ("L", "122 cm / 46,46\"", "54 cm / 21,26\"", "64 cm / 25,20\"", "89 cm / 35,43\""),
    ("XL", "132 cm / 48,82\"", "56 cm / 22,05\"", "65 cm / 25,59\"", "91 cm / 36,61\""),
    ("XXL", "142 cm / 51,18\"", "58 cm / 22,83\"", "66 cm / 25,98\"", "94 cm / 37,80\""),
    ("XXXL", "152 cm / 53,54\"", "60 cm / 23,62\"", "67 cm / 26,38\"", "96 cm / 38,98\""),
    ("XXXXL", "162 cm / 55,91\"", "62 cm / 24,41\"", "68 cm / 26,77\"", "99 cm / 40,16\""),
]


def draw_size_table(d, box, mobile=False):
    x, y, w, h = box
    if mobile:
        col_widths = [52, 138, 118, 118, 138]
        header_h, row_h = 34, 40
        header_font = font(FONT_BOLD, 11)
        size_font = font(FONT_BOLD, 13)
        cell_font = font(FONT_BOLD, 12)
    else:
        col_widths = [90, 225, 190, 190, 190]
        header_h, row_h = 48, 55
        header_font = font(FONT_BOLD, 17)
        size_font = font(FONT_BOLD, 19)
        cell_font = font(FONT_BOLD, 16)
    headers = ["TAILLE", "POITRINE", "ÉPAULES", "MANCHES", "LONGUEUR"]
    total_h = header_h + row_h * len(SIZE_DATA)
    d.rounded_rectangle((x - 4, y - 4, x + w + 4, y + total_h + 4), radius=18 if not mobile else 10,
                        fill=(7, 8, 12, 224), outline=(*AMBER, 235), width=2)
    d.rounded_rectangle((x, y, x + w, y + header_h), radius=13 if not mobile else 8,
                        fill=(151, 67, 34, 238))
    xx = x
    for i, cw in enumerate(col_widths):
        d.text((xx + cw / 2, y + header_h / 2), headers[i], font=header_font, fill=IVORY, anchor="mm")
        xx += cw
    yy = y + header_h
    for ridx, row in enumerate(SIZE_DATA):
        fill = (15, 17, 23, 232) if ridx % 2 == 0 else (25, 26, 31, 232)
        d.rectangle((x, yy, x + w, yy + row_h), fill=fill)
        xx = x
        for cidx, (cw, value) in enumerate(zip(col_widths, row)):
            if mobile and cidx > 0:
                value = value.replace(" / ", "\n")
            f = size_font if cidx == 0 else cell_font
            color = AMBER if cidx == 0 else IVORY
            if mobile and cidx > 0:
                d.multiline_text((xx + cw / 2, yy + row_h / 2), value, font=f, fill=color,
                                 anchor="mm", align="center", spacing=1)
            else:
                d.text((xx + cw / 2, yy + row_h / 2), value, font=f, fill=color, anchor="mm")
            xx += cw
        yy += row_h
    # Crisp grid drawn last for maximum legibility.
    xx = x
    for cw in col_widths[:-1]:
        xx += cw
        d.line((xx, y, xx, y + total_h), fill=(206, 143, 91, 125), width=1)
    yy = y + header_h
    for _ in SIZE_DATA:
        d.line((x, yy, x + w, yy), fill=(206, 143, 91, 105), width=1)
        yy += row_h
    return total_h


def module_size(size, mobile=False):
    bg = cover(scene("scene-06-enchanted-forest.png"), size, (0.36, 0.08))
    if mobile:
        bg = bg.filter(ImageFilter.GaussianBlur(3.0))
    im = bg.convert("RGBA")
    veil = Image.new("RGBA", size, (5, 7, 11, 158 if mobile else 72))
    im.alpha_composite(veil)
    gradient_overlay(im, "right", 242 if not mobile else 185, 0.72 if not mobile else 1.0)
    vignette(im, 95)
    d = ImageDraw.Draw(im, "RGBA")
    if mobile:
        draw_skull(d, (40, 37), 0.72)
        draw_skull(d, (560, 37), 0.72)
        d.text((300, 28), "S À 4XL  •  MESURES EN CM / POUCES", font=font(FONT_BOLD, 14), fill=AMBER, anchor="ma")
        draw_size_table(d, (18, 68, 564, 314), mobile=True)
        d.text((300, 426), "Comparez avec un vêtement similaire pour choisir votre taille.",
               font=font(FONT_BODY, 12), fill=(232, 229, 222), anchor="mm")
    else:
        draw_skull(d, (72, 67), 1.0)
        d.text((60, 128), "S À 4XL", font=font(FONT_DISPLAY, 38), fill=AMBER,
               stroke_width=2, stroke_fill=INK)
        draw_body(d, (62, 188), "Mesures indiquées en centimètres et en pouces.", 20, 390)
        pill(d, (62, 486), "HALLOWEEN  •  COSPLAY  •  FESTIVAL", scale=0.78)
        draw_size_table(d, (545, 86, 885, 433), mobile=False)
        d.text((987, 560), "Comparez avec un vêtement similaire pour choisir votre taille.",
               font=font(FONT_BODY, 15), fill=(232, 229, 222), anchor="mm")
    return im


def build_all():
    DESKTOP.mkdir(parents=True, exist_ok=True)
    MOBILE.mkdir(parents=True, exist_ok=True)
    PREVIEW.mkdir(parents=True, exist_ok=True)

    modules = [
        ("01-hero-full-image", module_hero),
        ("02-design-background-text", module_design),
        ("03-worlds-full-image", diagonal_triptych),
        ("05-comfort-full-image", module_comfort),
        ("06-fit-full-image", module_fit),
        ("07-size-guide-full-image", module_size),
    ]
    for obsolete in (
        DESKTOP / "07-occasion-full-image-1464x600.jpg",
        MOBILE / "07-occasion-full-image-600x450.jpg",
    ):
        obsolete.unlink(missing_ok=True)
    desktop_files, mobile_files = [], []
    for stem, fn in modules:
        dp = DESKTOP / f"{stem}-1464x600.jpg"
        mp = MOBILE / f"{stem}-600x450.jpg"
        save_jpg(fn(WIDE, mobile=False), dp)
        save_jpg(fn(PHONE, mobile=True), mp)
        desktop_files.append(dp)
        mobile_files.append(mp)

    for i in range(4):
        slug = ["castle", "nordic", "lanterns", "forest"][i]
        dp = DESKTOP / f"04-carousel-{i+1:02d}-{slug}-1464x600.jpg"
        mp = MOBILE / f"04-carousel-{i+1:02d}-{slug}-600x450.jpg"
        save_jpg(carousel_panel(i, WIDE, mobile=False), dp)
        save_jpg(carousel_panel(i, PHONE, mobile=True), mp)
        desktop_files.append(dp)
        mobile_files.append(mp)

    make_contact_sheet(sorted(desktop_files), PREVIEW / "desktop-contact-sheet.jpg", (732, 300), 2)
    make_contact_sheet(sorted(mobile_files), PREVIEW / "mobile-contact-sheet.jpg", (400, 300), 2)

    with (ROOT / "asset_manifest.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["module", "format", "desktop", "mobile", "french_title"])
        writer.writerow([1, "Premium Full Image", desktop_files[0].name, mobile_files[0].name, "ENTREZ DANS LA LÉGENDE"])
        writer.writerow([2, "Premium Background Image with Text", desktop_files[1].name, mobile_files[1].name, "LA NUIT SE PORTE EN DÉTAILS"])
        writer.writerow([3, "Premium Full Image", desktop_files[2].name, mobile_files[2].name, "TROIS MONDES. UNE MÊME PRÉSENCE."])
        writer.writerow([4, "Premium Simple Image Carousel", "04-carousel-01..04-*-1464x600.jpg", "04-carousel-01..04-*-600x450.jpg", "CHANGEZ DE DÉCOR, GARDEZ LE MYSTÈRE"])
        writer.writerow([5, "Premium Full Image", desktop_files[3].name, mobile_files[3].name, "DOUX. RESPIRANT. PRÊT POUR LA NUIT."])
        writer.writerow([6, "Premium Full Image", desktop_files[4].name, mobile_files[4].name, "DU S AU 4XL, TROUVEZ VOTRE ALLURE"])
        writer.writerow([7, "Premium Full Image", desktop_files[5].name, mobile_files[5].name, "GUIDE DES TAILLES — S À 4XL"])


def make_contact_sheet(files, output, cell, cols):
    cw, ch = cell
    pad = 18
    label_h = 32
    rows = math.ceil(len(files) / cols)
    sheet = Image.new("RGB", (cols * cw + (cols + 1) * pad, rows * (ch + label_h) + (rows + 1) * pad), (22, 23, 28))
    d = ImageDraw.Draw(sheet)
    for i, path in enumerate(files):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = pad + r * (ch + label_h + pad)
        thumb = cover(Image.open(path), cell)
        sheet.paste(thumb, (x, y))
        d.text((x, y + ch + 8), path.name, font=font(FONT_BOLD, 16), fill=(235, 235, 238))
    save_jpg(sheet, output)


if __name__ == "__main__":
    build_all()
