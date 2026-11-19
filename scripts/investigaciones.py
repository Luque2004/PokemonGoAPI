#!/usr/bin/env python3
"""Investigaciones de campo de ahora (Leek Duck) con las tareas, objetos y Pokémon en el español del juego.

Uso:
    python3 scripts/investigaciones.py                          # descarga leekduck.com/research y los textos del juego
    python3 scripts/investigaciones.py --html PAGINA [--textos DIR]   # pruebas: página ya descargada
                                                                # DIR: carpeta con i18n_english.json e i18n_spanish.json

- Tareas y recompensas (Pokémon con su PC, si puede ser variocolor, objetos y caramelos): leekduck.com/research.
- Los textos en español salen de los del juego (PokeMiners/pogo_assets, i18n_english.json → i18n_spanish.json): una
  tarea solo se traduce si su texto en inglés es exactamente uno del juego (con su número). Las traducciones se guardan
  en el JSON y se reutilizan si un día no se pueden descargar los textos. Lo que no se encuentre se queda en inglés y se avisa.
Escribe datos/investigaciones.json SOLO si la página se ha leído bien, y dice si ha cambiado (IGUAL / CAMBIA).
"""
import html, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://leekduck.com/research/"
SALIDA = os.path.join(ROOT, "datos", "investigaciones.json")
REPO_TEXTOS = "https://github.com/PokeMiners/pogo_assets.git"
RUTA_TEXTOS = "Texts/Latest APK/JSON"
CATEGORIAS = {"Catching Tasks": "Capturas", "Throwing Tasks": "Lanzamientos", "Battling Tasks": "Combates",
              "Exploring Tasks": "Exploración", "Training Tasks": "Entrenamiento", "Buddy & Friendship Tasks": "Compañero y amistad",
              "Team GO Rocket Tasks": "Team GO Rocket", "Sponsored Tasks": "Patrocinadas"}
FORMAS = {"Alolan": "de Alola", "Galarian": "de Galar", "Hisuian": "de Hisui", "Paldean": "de Paldea"}


def tx(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ")).strip()


def get(url):
    r = subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", "--retry", "2", "--max-time", "45", url], capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def textos(carpeta):
    """{inglés: español} de los textos del juego, o None si no se pueden leer."""
    if not carpeta:
        carpeta = tempfile.mkdtemp(prefix="pogo-textos-")
        ok = subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", REPO_TEXTOS, carpeta],
                            capture_output=True).returncode == 0 and subprocess.run(
            ["git", "-C", carpeta, "sparse-checkout", "set", "--no-cone", RUTA_TEXTOS + "/i18n_english.json",
             RUTA_TEXTOS + "/i18n_spanish.json"], capture_output=True).returncode == 0
        if not ok:
            return None
        carpeta = os.path.join(carpeta, RUTA_TEXTOS)

    def leer(f):
        d = json.load(open(os.path.join(carpeta, f), encoding="utf-8"))["data"]
        return dict(zip(d[0::2], d[1::2])) if isinstance(d, list) else d
    try:
        en, es = leer("i18n_english.json"), leer("i18n_spanish.json")
    except (OSError, ValueError, KeyError):
        return None
    return en, es


class Traductor:
    def __init__(self, t, antes):
        self.antes = antes  # {inglés: español} de la vez anterior
        self.usadas, self.faltan = {}, []
        self.en, self.es = t if t else ({}, {})
        self.exactas, self.plantillas = {}, []
        evento = re.compile(r"\d{2}|festival|_event|day_|fest|tour|anniv|season|special_dialogue", re.I)
        for k in sorted(self.en, key=lambda k: (bool(evento.search(k)), len(k), k)):
            v, e = self.en[k].strip(), self.es.get(k, "").strip()
            if not v or not e or (e == v and re.search(r"[a-z]{3}", v)):  # sin traducir en el juego
                continue
            self.exactas.setdefault(v, e)
            if "{0}" in v and "{1}" not in v and len(v) < 120:
                rx = "^" + re.escape(v).replace(re.escape("{0}"), r"(\d[\d,.]*)") + "$"
                self.plantillas.append((re.compile(rx), e))

    def __call__(self, s):
        if not s:
            return s
        r = self.exactas.get(s)
        if r is None:
            for rx, e in self.plantillas:
                m = rx.match(s)
                if m:
                    n = m.group(1).replace(",", "").replace(".", "")
                    r = e.replace("{0}", "{:,}".format(int(n)).replace(",", ".") if n.isdigit() and len(n) > 4 else m.group(1))
                    break
        if r is None:
            r = self.antes.get(s)
        if r is None:
            if s not in self.faltan:
                self.faltan.append(s)
            return s
        self.usadas[s] = r
        return r

    def pokemon(self, nombre_en, icono):
        """Nombre del juego en español por su número de la Pokédex, con la forma regional si la tiene."""
        m = re.match(r"pm(\d+)", icono or "")
        base = self.es.get("pokemon_name_%04d" % int(m.group(1))) if m else None
        forma = next((v for k, v in FORMAS.items() if nombre_en.startswith(k + " ")), "")
        if base:
            r = base + (" " + forma if forma else "")
            self.usadas[nombre_en] = r
            return r
        return self.antes.get(nombre_en) or (nombre_en if not forma else nombre_en.split(" ", 1)[1] + " " + forma)

    def objeto(self, n):
        """Objetos, Megaenergía y Caramelos con el texto del juego."""
        m = re.match(r"(.+) Mega Energy$", n)
        if m and "{0} Mega Energy" in self.exactas:
            return self.exactas["{0} Mega Energy"].replace("{0}", m.group(1))
        m = re.match(r"(.+) Candy$", n)
        if m and n != "Rare Candy" and "{0} Candy" in self.exactas:
            return self.es.get("pokemon_info_candy_label", "Caramelos {0}").replace("{0}", m.group(1))
        k = next((k for k, v in self.en.items() if v == n and k.startswith("item_") and k.endswith("_name")), None)
        if k:
            self.usadas[n] = self.es[k]
            return self.es[k]
        if n == "Stardust" and "Stardust" in self.exactas:
            return self.exactas["Stardust"]
        return self(n)


def icono_de(src):
    m = re.search(r"pokemon_icons(?:_crop)?/(pm\d+(?:\.f[A-Z0-9_]+)?)\.icon\.png", src or "")
    return m.group(1) if m else ""


def recompensa(li, tr):
    tipo = (re.search(r'data-reward-type="([a-z]+)"', li) or [0, ""])[1]
    lab = re.search(r'<span class="reward-label">(.*?)</span></span>', li, re.S)
    lab = tx(lab.group(1)) if lab else ""
    cant = re.search(r'class="quantity">\s*×\s*([\d,.]+)', li)
    r = {"tipo": tipo, "cantidad": int(re.sub(r"[,.]", "", cant.group(1))) if cant else None}
    if tipo == "encounter":
        ico = icono_de(li)
        nombre_en = re.sub(r"\s*×.*$", "", lab)
        mx = re.search(r'class="max-cp"><div>Max CP</div>\s*(\d+)', li)
        mn = re.search(r'class="min-cp"><div>Min CP</div>\s*(\d+)', li)
        r.update({"nombre": tr.pokemon(nombre_en, ico), "nombre_en": nombre_en, "icono": ico,
                  "pc": [int(mn.group(1)), int(mx.group(1))] if mn and mx else None, "variocolor": "shiny-badge" in li})
    else:
        nombre_en = re.sub(r"\s*×\s*[\d,.]+$", "", lab).strip()
        ico = icono_de(li)  # caramelos y Megaenergía llevan el icono del Pokémon
        r.update({"nombre": tr.objeto(nombre_en), "nombre_en": nombre_en, "icono": ico})
    return r


MESES = {"Jan": "ene", "Feb": "feb", "Mar": "mar", "Apr": "abr", "May": "may", "Jun": "jun", "Jul": "jul", "Aug": "ago",
         "Sep": "sept", "Oct": "oct", "Nov": "nov", "Dec": "dic"}


def fechas_es(s):
    """'Sep 8 – Dec 1 , 2026' → 'del 8 de sept al 1 de dic de 2026' ('' si no se entiende)."""
    m = re.match(r"([A-Z][a-z]{2})\w* (\d+)\s*[–-]\s*([A-Z][a-z]{2})\w* (\d+)\s*,\s*(\d{4})$", s)
    if not m or m.group(1) not in MESES or m.group(3) not in MESES:
        return ""
    return "del %s de %s al %s de %s de %s" % (m.group(2), MESES[m.group(1)], m.group(4), MESES[m.group(3)], m.group(5))


def leer(h, tr):
    cats = []
    for blk in re.split(r'(?=<div class="task-category)', h)[1:]:
        cab = re.match(r'<div class="task-category([^"]*)"([^>]*)>\s*<h2>(.*?)</h2>', blk, re.S)
        if not cab:
            continue
        fin = re.search(r'data-event-end="([^"]+)"', cab.group(2))
        nombre_en = tx(cab.group(3))
        evento = "event" in cab.group(1)
        nombre = CATEGORIAS.get(nombre_en) or ("Evento: " + re.sub(r"\s*Tasks$", "", nombre_en) if evento else tr(nombre_en))
        tareas = []
        for item in re.split(r'<li class="task-item">', blk)[1:]:
            t = re.search(r'<span class="task-text">(.*?)</span></span>', item, re.S)
            if not t:
                continue
            t_en = tx(t.group(1))
            rec = [recompensa(li, tr) for li in re.findall(r'(<li class="reward".*?</li>)', item, re.S)]
            rec = [x for x in rec if x["nombre"]]
            if t_en and rec:
                tareas.append({"tarea": tr(t_en), "tarea_en": t_en, "recompensas": rec})
        if tareas:
            cats.append({"nombre": nombre, "nombre_en": nombre_en, "evento": evento, "fin": fin.group(1) if fin else None, "tareas": tareas})
    fecha = re.search(r'<div class="page-date">Updated on <time datetime="([^"]+)"', h)
    av = None
    sec = re.search(r'<section class="research-breakthrough-section".*?</section>', h, re.S)
    if sec:
        s = sec.group(0)
        pk = []
        for li in re.findall(r'<li class="breakthrough-reward-item">(.*?)</li>', s, re.S):
            ico = icono_de(li)
            n = tx((re.search(r'<span class="reward-name">(.*?)</span>', li, re.S) or [0, ""])[1])
            pc = re.search(r'<span class="cp-label">CP</span>\s*(\d+)', li)
            if n and ico:
                pk.append({"nombre": tr.pokemon(n, ico), "nombre_en": n, "icono": ico, "pc": int(pc.group(1)) if pc else None,
                           "variocolor": "shiny-badge" in li})
        fechas = tx((re.search(r'<span class="breakthrough-dates">(.*?)</span>\s*</p>', s, re.S) or [0, ""])[1])
        av = {"fechas_en": fechas, "fechas": fechas_es(fechas), "pokemon": pk}
    return {"fuente": "Leek Duck", "url": URL, "actualizado": fecha.group(1) if fecha else "", "categorias": cats, "avance": av}


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
    d = leer(h, tr)
    n = sum(len(c["tareas"]) for c in d["categorias"])
    if len(d["categorias"]) < 3 or n < 20:
        print("Investigaciones: ERROR, no se ha podido leer bien la página de Leek Duck; no se toca el JSON")
        sys.exit(1)
    d["traducciones"] = dict(sorted(tr.usadas.items()))
    d["sin_traducir"] = tr.faltan
    estado = "IGUAL" if antes == d else "CAMBIA"
    if estado == "CAMBIA":
        os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
        with open(SALIDA, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print("Investigaciones: OK %d categorías, %d tareas%s (%s)" % (len(d["categorias"]), n, "" if t else ", sin los textos del juego (se usan las traducciones guardadas)", estado))
    if tr.faltan:
        print("  aviso: %d textos sin traducir (salen en inglés): %s" % (len(tr.faltan), " | ".join(tr.faltan)))


if __name__ == "__main__":
    main()
