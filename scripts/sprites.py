#!/usr/bin/env python3
"""Hoja de iconos de Pokémon (iconos del juego, PokeMiners/pogo_assets) para la pestaña Rocket.

Uso:
  python3 sprites.py lista  ALL.txt SEL.txt            # elige qué iconos entran (nombres de archivo)
  python3 sprites.py hoja   DIR SEL.txt OUT.webp IDS.txt CELDA COLUMNAS
"""
import re, sys

COSTUME = re.compile(r"\d|COPY|COSTUME|TIARA|^S$")


def lista(all_txt, out):
    names = [l.strip() for l in open(all_txt) if l.strip()]
    base = {int(m.group(1)): n for n in names if (m := re.fullmatch(r"pm(\d+)\.icon\.png", n))}
    sel = [base[d] for d in sorted(base)]
    extra = []
    for n in names:
        m = re.fullmatch(r"pm(\d+)\.f([A-Z0-9_]+)\.icon\.png", n)
        if not m:
            continue
        dex, form = int(m.group(1)), m.group(2)
        # todas las formas menos los disfraces de eventos (llevan año o número): regionales, Mega, Primigenio,
        # Gigamax y formas especiales (Kyurem Blanco, Necrozma Melena Crepuscular, Zacian Espada Suprema…)
        if not COSTUME.search(form):
            extra.append(n)
    key = lambda n: (int(re.match(r"pm(\d+)", n).group(1)), n)
    sel += sorted(set(extra), key=key)
    open(out, "w").write("\n".join(sel) + "\n")
    print(len(base), "normales +", len(set(extra)), "formas =", len(sel))


def hoja(d, sel_txt, out, ids_txt, cell, cols):
    from PIL import Image
    cell, cols = int(cell), int(cols)
    names = [l.strip() for l in open(sel_txt) if l.strip()]
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0))
    ids, pad = [], max(1, cell // 36)
    for i, n in enumerate(names):
        im = Image.open(f"{d}/{n}").convert("RGBA")
        box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
        if box:
            im = im.crop(box)
        s = (cell - 2 * pad) / max(im.size)
        im = im.resize((max(1, round(im.width * s)), max(1, round(im.height * s))), Image.LANCZOS)
        x, y = (i % cols) * cell, (i // cols) * cell
        sheet.alpha_composite(im, (x + (cell - im.width) // 2, y + (cell - im.height) // 2))
        ids.append(n[: -len(".icon.png")])
    sheet.save(out, "WEBP", quality=68, method=6, alpha_quality=75)
    open(ids_txt, "w").write(",".join(ids))
    print(len(ids), "iconos", sheet.size)


if __name__ == "__main__":
    {"lista": lista, "hoja": hoja}[sys.argv[1]](*sys.argv[2:])
