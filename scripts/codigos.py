#!/usr/bin/env python3
"""Códigos promocionales de Pokémon GO que se pueden canjear ahora (Leek Duck), con las recompensas en español.

Uso:
    python3 scripts/codigos.py                                  # descarga leekduck.com/promo-codes y los textos del juego
    python3 scripts/codigos.py --html PAGINA [--textos DIR]     # pruebas: página ya descargada

Escribe datos/codigos.json SOLO si la página se ha leído bien y dice si ha cambiado (IGUAL / CAMBIA).
Si hay códigos que no estaban la vez anterior, lo dice en una línea «NUEVOS: …» para avisar al móvil.
Los nombres de los objetos salen de los textos del juego, como en investigaciones.py (lo usa: tienen que estar juntos).
"""
import json, os, re, sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from investigaciones import Traductor, textos, tx, get  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://leekduck.com/promo-codes/"
SALIDA = os.path.join(ROOT, "datos", "codigos.json")


def leer(h, tr):
    out = []
    for card in re.split(r'(?=<div class="promo-card[ "])', h)[1:]:
        if re.match(r'<div class="promo-card[^"]*\bexpired\b', card):
            continue  # caducado
        cod = re.search(r'<p class="text"[^>]*>\s*([A-Za-z0-9]+)\s*</p>', card)
        if not cod:
            continue
        exp = re.search(r'<span class="expiry"([^>]*)>(.*?)</span>', card, re.S)
        attrs, texto = (exp.group(1), tx(exp.group(2))) if exp else ("", "")
        cad = re.search(r'data-expires="(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}):\d{2} ([+-]\d{4})"', attrs)
        if texto.lower().startswith("expired"):
            continue
        if cad:  # hora local de cada jugador: se compara con un margen de un día
            fin = datetime.strptime(cad.group(1) + " " + cad.group(2) + " " + cad.group(3), "%Y-%m-%d %H:%M %z")
            if (datetime.now(timezone.utc) - fin).total_seconds() > 86400:
                continue
        rec = []
        for li in re.findall(r'(<li class="reward".*?</li>)', card, re.S):
            lab = tx((re.search(r'<span class="reward-label">(.*?)</span>\s*(?:</li>|$)', li, re.S) or [0, ""])[1])
            cant = re.search(r'class="quantity">\s*×\s*([\d,.]+)', li)
            avatar = "avatar_items" in li
            n = re.sub(r"\s*×\s*[\d,.]+$", "", lab).strip()
            if n:
                rec.append({"nombre": n if avatar else tr.objeto(n), "nombre_en": n, "tipo": "avatar" if avatar else "objeto",
                            "cantidad": int(re.sub(r"[,.]", "", cant.group(1))) if cant else None})
        link = re.search(r'href="(https://store\.pokemongo\.com/offer-redemption\?passcode=[A-Za-z0-9]+)"', card)
        titulo = tx((re.search(r'<h3 class="title">(.*?)</h3>', card, re.S) or [0, ""])[1])
        out.append({"codigo": cod.group(1), "titulo_en": titulo, "recompensas": rec,
                    "caduca": cad.group(1) + " " + cad.group(2) if cad else None,
                    "canjear": link.group(1) if link else None})
    fecha = re.search(r'<div class="page-date">Updated on <time datetime="([^"]+)"', h)
    return {"fuente": "Leek Duck", "url": URL, "actualizado": fecha.group(1) if fecha else "", "codigos": out}


def main():
    a = sys.argv[1:]
    pagina = a[a.index("--html") + 1] if "--html" in a else None
    carpeta = a[a.index("--textos") + 1] if "--textos" in a else None
    h = open(pagina, encoding="utf-8", errors="replace").read() if pagina else get(URL)
    antes = None
    if os.path.exists(SALIDA):
        with open(SALIDA, encoding="utf-8") as f:
            antes = json.load(f)
    t = textos(carpeta) if (carpeta or not pagina) else None
    tr = Traductor(t, (antes or {}).get("traducciones") or {})
    if 'class="promo-card' not in h:
        print("Códigos: ERROR, no se ha podido leer la página de Leek Duck; no se toca el JSON")
        sys.exit(1)
    d = leer(h, tr)
    d["traducciones"] = dict(sorted(tr.usadas.items()))
    estado = "IGUAL" if antes == d else "CAMBIA"
    if estado == "CAMBIA":
        os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
        with open(SALIDA, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print("Códigos: OK %d se pueden canjear (%s)" % (len(d["codigos"]), estado))
    viejos = {c["codigo"] for c in (antes or {}).get("codigos", [])}
    nuevos = [c for c in d["codigos"] if c["codigo"] not in viejos]
    if antes is not None and nuevos:
        def caduca(c):
            if not c["caduca"]:
                return ""
            y, m, dd = c["caduca"][:10].split("-")
            return " hasta el %d/%d/%s" % (int(dd), int(m), y)
        print("NUEVOS: " + " · ".join("%s (%s)%s" % (c["codigo"], ", ".join(
            (r["nombre"] + (" ×%d" % r["cantidad"] if r["cantidad"] else "")) for r in c["recompensas"]) or c["titulo_en"], caduca(c))
            for c in nuevos))


if __name__ == "__main__":
    main()
