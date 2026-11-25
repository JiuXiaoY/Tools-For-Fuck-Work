"""Render editable HTML/CSS layouts as Amazon.es Premium A+ JPEG assets.

Product photographs remain unmodified image elements. The two generated
editorial photographs are stored next to this script in ``_generated``.
"""

from __future__ import annotations

import csv
import html
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parent
PHOTO = ROOT.parent / "photo"
HALL = (ROOT / "_generated" / "hall.png").as_uri()
THRESHOLD = (ROOT / "_generated" / "threshold.png").as_uri()
PRODUCT = (PHOTO / "51bWV8uXyzL._AC_SX679_.jpg").as_uri()
MODEL = (PHOTO / "51uZZeXBODL._AC_SX679_.jpg").as_uri()
STUDIO = (PHOTO / "61o-3vJqlLL._AC_SX679_.jpg").as_uri()

NAMES = [
    "01-hero",
    "02-silhouette",
    "03-threshold",
    "04-design-details",
    "05-occasions",
    "06-size-guide",
    "07-finale",
]

ALT = [
    "Vestido negro de bruja con mangas de murciélago en una escena gótica de Halloween",
    "Vestido negro largo con mangas amplias, escote redondeado y bajo en puntas",
    "Vestido negro de bruja en una entrada de piedra iluminada para Halloween",
    "Detalles visibles del vestido: mangas tipo ala, escote y bajo largo en puntas",
    "Vestido de bruja negro presentado para Halloween, fiesta temática y cosplay",
    "Guía de tallas en centímetros para el vestido de bruja, de S a XXXL",
    "Vestido de bruja negro de silueta sirena y mangas en forma de alas",
]


def xmp_tag_jpeg(path: Path) -> None:
    """Mark final scenes with synthetic people for Amazon's A+ upload flow."""
    packet = (
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/">'
        '<dc:subject><rdf:Bag><rdf:li>contains-synthetic-performer</rdf:li>'
        '</rdf:Bag></dc:subject></rdf:Description></rdf:RDF></x:xmpmeta>'
    ).encode("utf-8")
    payload = b"http://ns.adobe.com/xap/1.0/\x00" + packet
    segment = b"\xff\xe1" + (len(payload) + 2).to_bytes(2, "big") + payload
    data = path.read_bytes()
    if not data.startswith(b"\xff\xd8"):
        raise ValueError(f"Not a JPEG: {path}")
    path.write_bytes(data[:2] + segment + data[2:])


def card(src: str, label: str, cls: str = "") -> str:
    return f'<div class="photo-card {cls}"><img src="{src}"><span>{html.escape(label)}</span></div>'


def module_html(n: int) -> str:
    if n == 1:
        return f"""
        <div class="scene-img" style="background-image:url('{HALL}')"></div>
        <div class="hero-shade"></div><div class="rune hero-rune">✦</div>
        <div class="hero-copy"><div class="eyebrow orange">COLECCIÓN HALLOWEEN</div>
        <div class="hero-title">La noche<br><em>tiene alas</em></div>
        <div class="stroke"></div><p>Vestido de bruja negro con mangas<br>de efecto murciélago</p></div>
        <div class="serial">01 / 07</div>"""
    if n == 2:
        return f"""
        <div class="cream-grain"></div><div class="feature-photo"><img src="{PRODUCT}"></div>
        <div class="feature-copy"><div class="eyebrow plum">EL DISEÑO</div>
        <h2>Una silueta<br>que impone</h2><p class="lead">Tres rasgos que definen el look.</p>
        <div class="feature-row"><b>01</b><div><strong>Mangas efecto ala</strong><small>Caída amplia que se despliega al levantar los brazos.</small></div></div>
        <div class="feature-row"><b>02</b><div><strong>Escote redondeado</strong><small>Una línea limpia en la parte delantera.</small></div></div>
        <div class="feature-row"><b>03</b><div><strong>Bajo en puntas</strong><small>Falda larga con remate de inspiración murciélago.</small></div></div>
        </div><div class="side-word">WITCH DRESS</div>"""
    if n == 3:
        return f"""
        <div class="scene-img" style="background-image:url('{THRESHOLD}')"></div>
        <div class="threshold-shade"></div><div class="threshold-copy">
        <div class="eyebrow orange">UNA ENTRADA MEMORABLE</div>
        <h2>Del umbral<br><em>a la fiesta</em></h2>
        <div class="stroke"></div><p>Una presencia teatral para Halloween<br>y celebraciones temáticas.</p>
        </div><div class="serial">03 / 07</div>"""
    if n == 4:
        return f"""
        <div class="detail-head"><div class="eyebrow orange">MÍRALA DE CERCA</div>
        <h2>Detalles que dibujan la noche</h2></div>
        <div class="detail-grid">
        {card(MODEL, '01 · MANGAS AMPLIAS', 'wing')}
        {card(MODEL, '02 · ESCOTE REDONDEADO', 'neck')}
        {card(PRODUCT, '03 · BAJO EN PUNTAS', 'hem')}
        </div><div class="detail-rule"></div>"""
    if n == 5:
        return f"""
        <div class="occasion-head"><div class="eyebrow plum">ELIGE TU ESCENA</div>
        <h2>Una silueta, muchas noches</h2></div>
        <div class="occasion-grid">
        {card(HALL, 'HALLOWEEN', 'occ1')}
        {card(THRESHOLD, 'FIESTA TEMÁTICA', 'occ2')}
        {card(STUDIO, 'COSPLAY', 'occ3')}
        </div>"""
    if n == 6:
        rows = [("S",82,69,90,60,166),("M",86,73,94,61,168),
                ("L",90,77,98,62,170),("XL",94,81,102,63,172),
                ("XXL",98,85,106,64,174),("XXXL",102,89,110,65,176)]
        trs = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in row) + "</tr>" for row in rows)
        return f"""
        <div class="size-photo"><img src="{PRODUCT}"></div>
        <div class="size-content"><div class="eyebrow orange">ANTES DE ELEGIR</div>
        <h2>Guía de tallas</h2><p>Medidas en centímetros · S–XXXL</p>
        <table><thead><tr><th>Talla</th><th>Pecho</th><th>Cintura</th><th>Cadera</th><th>Manga</th><th>Largo</th></tr></thead>
        <tbody>{trs}</tbody></table>
        <div class="size-foot">Consulta las medidas antes de seleccionar tu talla.</div></div>"""
    return f"""
        <div class="final-text"><div class="eyebrow orange">VESTIDO DE BRUJA · HALLOWEEN</div>
        <h2>Tu noche.<br><em>Tu silueta.</em></h2>
        <div class="stroke"></div><p>Alas al moverte. Una silueta sirena.<br>Un look hecho para entrar en escena.</p>
        <div class="final-pills"><span>ALAS</span><span>SIRENA</span><span>HALLOWEEN</span></div>
        </div><div class="final-arch"><img src="{STUDIO}"></div>
        <div class="moon"></div>"""


CSS = r"""
*{box-sizing:border-box} html,body{margin:0;background:#111;color:#fff}
body{font-family:'Segoe UI',Arial,sans-serif}.frame{width:1464px;height:600px;position:relative;overflow:hidden;margin:0}
.scene-img{position:absolute;inset:0;background-size:cover;background-position:center}
.eyebrow{font-family:'Bahnschrift SemiBold Condensed','Arial Narrow',sans-serif;font-weight:700;letter-spacing:4px;font-size:20px}
.orange{color:#e5a056}.plum{color:#6b3b5a}.stroke{height:4px;width:102px;background:#e5a056;margin:22px 0 22px}
p{margin:0;font-family:Georgia,serif}.serial{position:absolute;bottom:34px;right:46px;color:#e8d8c6;font:15px 'Bahnschrift Condensed',sans-serif;letter-spacing:2px}
.hero-shade{position:absolute;inset:0;background:linear-gradient(90deg,rgba(10,7,20,.94) 0%,rgba(10,7,20,.84) 27%,rgba(10,7,20,.44) 49%,transparent 69%)}
.hero-copy{position:absolute;top:128px;left:77px;width:650px}.hero-title{font-family:'Baskerville Old Face',Georgia,serif;font-size:92px;line-height:.96;color:#fff8eb;margin:23px 0 0;letter-spacing:-2px}
.hero-title em{font-family:'Old English Text MT',Georgia,serif;font-style:normal;color:#f2d5a9;font-size:92px}
.hero-copy p{font-size:27px;line-height:1.3;color:#fff2df}.rune{position:absolute;color:#e8aa63;font-size:35px}.hero-rune{left:688px;top:90px}
.cream-grain{position:absolute;inset:0;background:radial-gradient(circle at 16% 30%,#fffaf0,#f1e7d8 68%,#e5d3b9)}
.feature-photo{position:absolute;left:62px;top:43px;width:540px;height:515px;background:#fff;border:1px solid #caa66d;box-shadow:20px 20px 0 #d8c5a8;overflow:hidden}
.feature-photo img{width:100%;height:100%;object-fit:contain}.feature-copy{position:absolute;left:665px;top:55px;width:690px;color:#24192a}
.feature-copy h2,.occasion-head h2{font:66px/1.0 'Baskerville Old Face',Georgia,serif;margin:14px 0 8px}.feature-copy .lead{font-size:24px;color:#735d65;margin-bottom:26px}
.feature-row{display:flex;align-items:flex-start;border-top:1px solid #cdb9a6;padding:14px 0;gap:26px}.feature-row b{font:24px 'Bahnschrift Condensed',sans-serif;color:#b26540}.feature-row strong{display:block;font:26px 'Bahnschrift SemiBold Condensed',sans-serif;letter-spacing:.6px}.feature-row small{display:block;font:18px/1.25 Georgia,serif;margin-top:4px;color:#6b5960}
.side-word{position:absolute;left:-112px;top:270px;transform:rotate(-90deg);color:#7c3d4f;letter-spacing:5px;font:16px 'Bahnschrift Condensed',sans-serif}
.threshold-shade{position:absolute;inset:0;background:linear-gradient(90deg,transparent 40%,rgba(4,9,23,.48) 57%,rgba(4,9,23,.94) 100%)}
.frame[data-n='3'] .scene-img{background-size:auto 100%;background-position:left center;background-repeat:no-repeat;background-color:#08101e}
.threshold-copy{position:absolute;left:870px;top:134px;width:510px}.threshold-copy h2{font:74px/1.02 'Baskerville Old Face',Georgia,serif;margin:20px 0 0;color:#fff3de}.threshold-copy h2 em{font-family:'Old English Text MT',Georgia,serif;font-style:normal;color:#f7c985}.threshold-copy p{font:24px/1.35 Georgia,serif;color:#fff4e5}
.frame[data-n='4']{background:radial-gradient(circle at 90% 10%,#3c1e43,#130f1d 65%)}
.detail-head{position:absolute;top:28px;left:64px}.detail-head h2{font:58px 'Baskerville Old Face',Georgia,serif;color:#f7eddd;margin:7px 0 0}.detail-grid{position:absolute;top:154px;left:63px;right:63px;display:grid;grid-template-columns:repeat(3,1fr);gap:20px;height:393px}
.photo-card{position:relative;overflow:hidden;background:#fff}.photo-card img{width:100%;height:100%;object-fit:cover}.photo-card span{position:absolute;bottom:0;left:0;right:0;background:linear-gradient(0deg,rgba(11,8,19,.95),rgba(11,8,19,.65));padding:18px 24px;color:#fff5e7;font:20px 'Bahnschrift SemiBold Condensed',sans-serif;letter-spacing:2px}
.detail-grid .wing img{object-position:center 18%}.detail-grid .neck img{object-position:center 0%;transform:scale(1.8);transform-origin:center 8%}.detail-grid .hem img{object-position:center 100%;transform:scale(1.45);transform-origin:center 100%}
.detail-rule{position:absolute;left:63px;right:63px;bottom:30px;height:2px;background:#a9634d}
.frame[data-n='5']{background:#f0e3d0;color:#24192a}.occasion-head{position:absolute;left:64px;top:27px}.occasion-head h2{font-size:56px;margin:8px 0}
.occasion-grid{position:absolute;top:143px;left:62px;right:62px;bottom:34px;display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
.occasion-grid .photo-card{border:4px solid #e6b575}.occasion-grid .occ1 img{object-position:76% center}.occasion-grid .occ2 img{object-position:24% center}.occasion-grid .occ3 img{object-position:center center}
.occasion-grid .photo-card span{font-size:23px;background:linear-gradient(0deg,rgba(26,9,26,.95),transparent);padding:60px 22px 18px}
.frame[data-n='6']{background:radial-gradient(circle at 20% 20%,#37213c,#151424 60%,#100d19)}
.size-photo{position:absolute;left:44px;top:50px;width:355px;height:500px;background:white;border:2px solid #c5955f;overflow:hidden}.size-photo img{width:100%;height:100%;object-fit:contain}
.size-content{position:absolute;left:451px;top:42px;width:950px}.size-content h2{font:65px 'Baskerville Old Face',Georgia,serif;margin:2px 0 0;color:#fff4e1}.size-content p{font:22px Georgia,serif;color:#dcc9c5;margin:0 0 18px}
table{border-collapse:collapse;width:100%;font:21px 'Bahnschrift SemiCondensed',Arial,sans-serif;text-align:center}th{background:#b86c48;color:#fff7e9;height:48px;letter-spacing:.5px}td{height:49px;background:#fff9ee;color:#302230;border-bottom:1px solid #ddcbb9}tr:nth-child(even) td{background:#f2e7dc}td:first-child{font-weight:700;color:#653046}
.size-foot{margin-top:15px;font:19px Georgia,serif;color:#dbc7c3}
.frame[data-n='7']{background:radial-gradient(circle at 95% 10%,#4e234e,#1b1129 58%,#120d1a)}
.final-text{position:absolute;top:116px;left:72px;z-index:3;width:650px}.final-text h2{font:83px/.98 'Baskerville Old Face',Georgia,serif;color:#f9ebd7;margin:25px 0 0}.final-text h2 em{font-family:'Old English Text MT',Georgia,serif;font-style:normal;color:#efbd80}.final-text p{font:24px/1.35 Georgia,serif;color:#f2deda}
.final-pills{display:flex;gap:12px;margin-top:30px}.final-pills span{border:1px solid #c88256;color:#f3c18d;padding:8px 15px;font:17px 'Bahnschrift SemiBold Condensed',sans-serif;letter-spacing:2px}
.final-arch{position:absolute;left:780px;top:-72px;width:590px;height:700px;overflow:hidden;border-radius:290px 290px 0 0;border:8px solid #9b634e;box-shadow:0 0 0 15px #301929,0 0 0 17px #ae7958}.final-arch img{width:100%;height:100%;object-fit:cover;object-position:center 28%}
.moon{position:absolute;right:29px;top:55px;width:150px;height:150px;border-radius:50%;background:#d5baaf;box-shadow:0 0 90px 15px #a66789;opacity:.47}
/* Mobile layouts are composed separately; source photos remain their own elements. */
.mobile.frame{width:600px;height:450px}.mobile .eyebrow{font-size:14px;letter-spacing:2.4px}.mobile .stroke{width:65px;height:3px;margin:13px 0}.mobile .serial{font-size:10px;right:16px;bottom:13px}
.mobile .hero-shade{background:linear-gradient(0deg,rgba(9,7,20,.96),rgba(9,7,20,.82) 38%,transparent 82%)}
.mobile .scene-img{background-position:72% center}.mobile .hero-copy{top:auto;bottom:31px;left:25px;width:540px}.mobile .hero-title{font-size:53px;margin:7px 0}.mobile .hero-title em{font-size:53px}.mobile .hero-copy p{font-size:16px}.mobile .hero-rune{left:28px;top:22px;font-size:22px}
.mobile .feature-photo{left:18px;top:46px;width:257px;height:357px;box-shadow:8px 8px 0 #d8c5a8}.mobile .feature-copy{left:297px;top:48px;width:286px}.mobile .feature-copy h2{font-size:33px;margin:8px 0}.mobile .feature-copy .lead{font-size:14px;margin-bottom:8px}.mobile .feature-row{gap:9px;padding:8px 0}.mobile .feature-row b{font-size:15px}.mobile .feature-row strong{font-size:16px}.mobile .feature-row small{font-size:12px;margin-top:1px}.mobile .side-word{display:none}
.mobile .threshold-shade{background:linear-gradient(0deg,rgba(4,9,23,.97),rgba(4,9,23,.65) 38%,transparent 75%)}
.mobile.frame[data-n='3'] .scene-img{background-size:cover;background-position:42% center}
.mobile .threshold-copy{left:25px;top:auto;bottom:29px;width:540px}.mobile .threshold-copy h2{font-size:47px;margin:10px 0 0}.mobile .threshold-copy p{font-size:16px}
.mobile .detail-head{top:17px;left:19px}.mobile .detail-head h2{font-size:27px;margin:4px 0}.mobile .detail-grid{top:104px;left:15px;right:15px;height:313px;gap:7px}.mobile .photo-card span{font-size:11px;letter-spacing:.3px;padding:10px 7px}.mobile .detail-rule{left:15px;right:15px;bottom:18px}
.mobile .occasion-head{top:15px;left:18px}.mobile .occasion-head h2{font-size:28px;margin:5px 0}.mobile .occasion-grid{top:96px;left:15px;right:15px;bottom:18px;gap:7px}.mobile .occasion-grid .photo-card{border-width:2px}.mobile .occasion-grid .photo-card span{font-size:13px;letter-spacing:.5px;padding:40px 7px 10px}
.mobile .size-photo{display:none}.mobile .size-content{left:17px;top:17px;width:566px}.mobile .size-content h2{font-size:36px}.mobile .size-content p{font-size:14px;margin-bottom:15px}.mobile table{font-size:14px}.mobile th{height:39px}.mobile td{height:42px}.mobile .size-foot{font-size:12px;margin-top:12px}
.mobile .final-text{top:51px;left:25px;width:350px}.mobile .final-text h2{font-size:49px;margin:12px 0 0}.mobile .final-text p{font-size:14px}.mobile .final-pills{gap:4px;margin-top:17px}.mobile .final-pills span{font-size:10px;padding:5px 7px;letter-spacing:.6px}.mobile .final-arch{left:350px;top:75px;width:235px;height:396px;border-width:4px;box-shadow:0 0 0 7px #301929,0 0 0 9px #ae7958}.mobile .moon{right:18px;top:18px;width:72px;height:72px}
"""


def document(mobile: bool) -> str:
    cls = "frame mobile" if mobile else "frame"
    frames = "\n".join(f'<section class="{cls}" data-n="{n}" id="m{n}">{module_html(n)}</section>' for n in range(1, 8))
    return f'<!doctype html><html lang="es"><head><meta charset="utf-8"><style>{CSS}</style></head><body>{frames}</body></html>'


def main() -> None:
    build = ROOT / "_build"
    build.mkdir(exist_ok=True)
    (ROOT / "mobile_600x450").mkdir(exist_ok=True)
    (ROOT / "_preview").mkdir(exist_ok=True)
    synthetic = {1, 3, 5}  # modules containing AI-generated people
    upload_rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for mobile in (False, True):
            page_file = build / ("mobile.html" if mobile else "desktop.html")
            page_file.write_text(document(mobile), encoding="utf-8")
            page = browser.new_page(viewport={"width": 600 if mobile else 1464, "height": 850}, device_scale_factor=1)
            page.goto(page_file.as_uri(), wait_until="load")
            page.evaluate("document.fonts.ready")
            page.locator("img").evaluate_all("els => Promise.all(els.map(e => e.decode().catch(() => {})))")
            for n, name in enumerate(NAMES, start=1):
                file = (ROOT / "mobile_600x450" if mobile else ROOT) / f"{name}-{'mobile-600x450' if mobile else '1464x600'}.jpg"
                page.locator(f"#m{n}").screenshot(path=str(file), type="jpeg", quality=88)
                if n in synthetic:
                    xmp_tag_jpeg(file)
                if not mobile:
                    upload_rows.append({"order": n, "module": "Premium Full Image", "desktop_file": file.name,
                                        "mobile_file": f"mobile_600x450/{name}-mobile-600x450.jpg",
                                        "alt_text_es": ALT[n-1], "synthetic_person": "yes" if n in synthetic else "no"})
                print(file.relative_to(ROOT), file.stat().st_size)
            page.screenshot(path=str(ROOT / "_preview" / ("00-mobile-overview.png" if mobile else "00-desktop-overview.png")), full_page=True)
            page.close()
        browser.close()
    with (ROOT / "UPLOAD_INFO.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=upload_rows[0].keys())
        writer.writeheader()
        writer.writerows(upload_rows)


if __name__ == "__main__":
    main()
