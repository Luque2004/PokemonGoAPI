#!/usr/bin/env python3
"""Incursiones de ahora y próximas (Leek Duck) con sus mejores counters (Pokémon GO Hub).

Uso (desde /tmp/hub):
  python3 scripts/raids.py                        # descarga todo y escribe datos/raids.json (IGUAL / CAMBIA)
  python3 scripts/raids.py --html CARPETA         # usa páginas ya descargadas (para pruebas)
  python3 scripts/raids.py traducir ARCHIVO.json  # añade traducciones {"texto en inglés": "texto en español"}

- Jefes, PC, clima, variocolor y fechas de cada rotación: leekduck.com/raids/manifest.json y /raids/<slug>.html.
  Las horas de Leek Duck son hora local de cada jugador: aquí se guardan como hora de España.
- Counters: db.pokemongohub.net/es/pokemon/<id>/counters (simulados contra ese jefe; nivel 50, 15/15/15).
- Debilidades: tabla de tipos del juego (×1,6 supereficaz, ×2,56 doble).
- Los títulos y notas de Leek Duck vienen en inglés: se traducen una vez (ver «traducir») y se reutilizan.
Escribe datos/raids.json SOLO si todo se ha leído bien.
"""
import html, json, os, re, subprocess, sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(ROOT, "datos", "raids.json")
LD = "https://leekduck.com"
HUB = "https://db.pokemongohub.net/es/pokemon/%s/counters"
N_COUNTERS = 12
DIAS_VISTA = 21  # rotaciones que empiezan en las próximas 3 semanas
TIPOS = ["normal", "fighting", "flying", "poison", "ground", "rock", "bug", "ghost", "steel", "fire", "water", "grass",
         "electric", "psychic", "ice", "dragon", "dark", "fairy"]
# Tabla de tipos: ataque → (supereficaz, poco eficaz, inmune)
TABLA = {
    "normal": ("", "rock steel", "ghost"),
    "fighting": ("normal ice rock dark steel", "poison flying psychic bug fairy", "ghost"),
    "flying": ("grass fighting bug", "electric rock steel", ""),
    "poison": ("grass fairy", "poison ground rock ghost", "steel"),
    "ground": ("fire electric poison rock steel", "grass bug", "flying"),
    "rock": ("fire ice flying bug", "fighting ground steel", ""),
    "bug": ("grass psychic dark", "fire fighting poison flying ghost steel fairy", ""),
    "ghost": ("psychic ghost", "dark", "normal"),
    "steel": ("ice rock fairy", "fire water electric steel", ""),
    "fire": ("grass ice bug steel", "fire water rock dragon", ""),
    "water": ("fire ground rock", "water grass dragon", ""),
    "grass": ("water ground rock", "fire grass poison flying bug dragon steel", ""),
    "electric": ("water flying", "electric grass dragon", "ground"),
    "psychic": ("fighting poison", "psychic steel", "dark"),
    "ice": ("grass ground flying dragon", "fire water ice steel", ""),
    "dragon": ("dragon", "steel", "fairy"),
    "dark": ("psychic ghost", "fighting dark fairy", ""),
    "fairy": ("fighting dragon dark", "fire poison steel", ""),
}
CLIMA = {"sunny": "Soleado", "clear": "Despejado", "rainy": "Lluvia", "partly cloudy": "Parcialmente nublado",
         "cloudy": "Nublado", "windy": "Viento", "snow": "Nieve", "fog": "Niebla"}


def tx(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ")).strip()


def get(url, carpeta=None):
    if carpeta:  # pruebas: páginas guardadas con el nombre de la URL
        ruta = os.path.join(carpeta, re.sub(r"[^A-Za-z0-9._-]+", "_", url))
        return open(ruta, encoding="utf-8", errors="replace").read() if os.path.exists(ruta) else ""
    r = subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", "--retry", "2", "--max-time", "45", url], capture_output=True)
    return r.stdout.decode("utf-8", "replace")


def hora(s, local):
    """'2026-11-14 10:00:00 -0800' → hora de España. Si es hora local de cada jugador, son las 10:00 en España."""
    if local:
        return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ)
    return datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S %z").astimezone(TZ)


def mult(ataque, defensa):
    se, nve, inm = (set(x.split()) for x in TABLA[ataque])
    m = 1.0
    for d in defensa:
        m *= 1.6 if d in se else 0.625 if d in nve else 0.390625 if d in inm else 1.0
    return m


def debilidades(tipos):
    out = [{"tipo": t, "x": round(mult(t, tipos), 2)} for t in TIPOS]
    return sorted([d for d in out if d["x"] > 1.01], key=lambda d: (-d["x"], TIPOS.index(d["tipo"])))


def icono_de(a):
    """Icono del juego (pm384.fMEGA…) a partir de la imagen de Pokémon GO Hub (384-mega.webp)."""
    m = re.search(r"(?:%2F|/)images(?:%2F|/)pokemon(?:%2F|/)([a-z0-9-]+)\.webp", a)
    if not m or not m.group(1).split("-")[0].isdigit():
        return ""
    p = m.group(1).split("-")
    resto = [x for x in p[1:] if x not in ("shadow", "dynamax", "purified")]
    return "pm" + p[0] + (".f" + "_".join(resto).upper() if resto else "")


def celda(tr, c):
    m = re.search(r'<td[^>]*data-column-id="%s"[^>]*>(.*?)</td>' % c, tr, re.S)
    return m.group(1) if m else ""


def ataque(c):
    n = re.search(r"<span>([^<]+)</span>", c)
    t = re.search(r'<img title="([A-Za-z]+)"', c)
    tipo = t.group(1).lower() if t else ""
    return tx(n.group(1)) if n else tx(c), "Movimiento de legado" in c, tipo if tipo in TIPOS else ""


def num(s):
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def slug_hub(icono):
    m = re.fullmatch(r"pm(\d+)(?:\.f([A-Z0-9_]+))?", icono)
    dex, forma = m.groups()
    return dex if not forma else dex + "-" + "_".join(w.capitalize() for w in forma.split("_"))


def disfraz(icono):
    f = icono.split(".f", 1)[1] if ".f" in icono else ""
    return bool(f) and bool(re.search(r"\d|COSTUME|COPY", f))


CACHE = {}


def counters(icono, carpeta):
    """(nombre en español, url, lista de counters) según Pokémon GO Hub, o (None, None, []) si no está."""
    if icono in CACHE:
        return CACHE[icono]
    res = (None, None, [], False)
    for ico, con_disfraz in ((icono, False), (icono.split(".")[0], True)):
        if con_disfraz and not disfraz(icono):
            break  # una forma de verdad (regional, Mega…) no se cambia por la especie: los counters serían otros
        url = HUB % slug_hub(ico)
        h = get(url, carpeta)
        t = re.search(r"<title>Mejores counters para (.+?) en Pokémon GO", h)
        if not t:
            continue
        F, tier = [], ""
        for tr in re.findall(r"<tr>(.*?)</tr>", h, re.S):
            a = celda(tr, "attacker_name")
            if "<a" not in a:
                continue
            tm = re.search(r'data-tier="([A-Z+]+)"', celda(tr, "tier"))
            tier = tm.group(1) if tm else tier
            nm = re.search(r'data-pokemon-chip-name="true">([^<]+)<', a)
            r1, l1, _ = ataque(celda(tr, "qm_name"))
            r2, l2, t2 = ataque(celda(tr, "cm_name"))
            F.append({"nombre": html.unescape(nm.group(1)).strip() if nm else tx(a), "icono": icono_de(a),
                      "rapido": r1, "cargado": r2, "tipo": t2, "legado": l1 or l2, "rapido_legado": l1, "cargado_legado": l2,
                      "edps": num(tx(celda(tr, "score"))), "tier": tier})
            if len(F) >= N_COUNTERS:
                break
        res = (html.unescape(t.group(1)).strip(), url, F, con_disfraz)
        break
    CACHE[icono] = res
    return res


def nombre_oscuro(n):
    m = re.match(r"(.+?) (Forma .+|Modo .+|Estilo .+)$", n)
    if m:
        return "%s oscuro (%s)" % (m.group(1), m.group(2))
    return n + " oscuro"


def etiqueta(lab):
    m = re.match(r"(\d)-Star", lab)
    if m:
        return m.group(1) + (" estrella" if m.group(1) == "1" else " estrellas")
    for en, es in (("Mega", "Mega"), ("Elite", "Élite"), ("Primal", "Primigenia"), ("Ultra Beast", "Ultraentes")):
        if en in lab:
            return es
    return lab


def niveles(h, sombra, carpeta, avisos):
    out = []
    for blk in re.split(r'(?=<div class="tier")', h)[1:]:
        lab = tx((re.search(r'<span class="tier-label">(.*?)</span>', blk, re.S) or [0, ""])[1])
        nota = tx((re.search(r'<p class="note">(.*?)</p>', blk, re.S) or [0, ""])[1])
        jefes = []
        for c in re.split(r'(?=<div class="card[ "])', blk)[1:]:
            en = tx((re.search(r'<p class="name[^"]*">(.*?)</p>', c, re.S) or [0, ""])[1])
            ico = re.search(r"pokemon_icons(?:_crop)?/(pm\d+(?:\.f[A-Z0-9_]+)?)\.icon\.png", c)
            tipos = [t.lower() for t in re.findall(r'title="([A-Za-z]+)" src="/assets/img/types', c) if t.lower() in TIPOS]
            pcs = [[int(a), int(b)] for a, b in re.findall(r"CP </span>\s*(\d+)\s*-\s*(\d+)", c)]
            clima = [CLIMA.get(x.lower(), x) for x in (tx(y) for y in re.findall(r'class="label">(.*?)</span>', c, re.S))]
            if not en or not ico or not tipos:
                continue
            icono = ico.group(1)
            oscuro = sombra or en.lower().startswith("shadow ")
            nombre, url, F, base = counters(icono, carpeta)
            if not nombre:
                avisos.append("sin counters en Pokémon GO Hub: %s (%s)" % (en, slug_hub(icono)))
                nombre = re.sub(r"^Shadow ", "", en)
            if base:
                nombre += " (con disfraz)"
            if oscuro:
                nombre = nombre_oscuro(nombre)
            jefes.append({"nombre": nombre, "nombre_en": en, "icono": icono, "oscuro": oscuro, "tipos": tipos,
                          "pc": pcs[0] if pcs else None, "pc_clima": pcs[1] if len(pcs) > 1 else None,
                          "clima": clima, "variocolor": "shiny-icon" in c, "debil": debilidades(tipos),
                          "counters": F, "hub": url})
        if jefes:
            out.append({"nivel": etiqueta(lab), "nivel_en": lab, "nota_en": nota, "jefes": jefes})
    return out


def traducir_doc(d, tr):
    pend = set()
    for r in d["rotaciones"]:
        r["titulo"] = tr.get(r["titulo_en"], "")
        if not r["titulo"]:
            pend.add(r["titulo_en"])
        for n in r["niveles"]:
            n["nota"] = tr.get(n["nota_en"], "") if n["nota_en"] else ""
            if n["nota_en"] and not n["nota"]:
                pend.add(n["nota_en"])
    usados = {r["titulo_en"] for r in d["rotaciones"]} | {n["nota_en"] for r in d["rotaciones"] for n in r["niveles"] if n["nota_en"]}
    d["traducciones"] = {k: v for k, v in sorted(tr.items()) if k in usados}
    return sorted(pend)


def leer_antes():
    if os.path.exists(SALIDA):
        with open(SALIDA, encoding="utf-8") as f:
            return json.load(f)
    return None


def escribir(d):
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write("\n")


def pendientes_txt(p):
    return "" if not p else "; %d textos sin traducir (añádelos con «traducir»):\n" % len(p) + "\n".join("  - " + x for x in p)


def main():
    a = sys.argv[1:]
    if a[:1] == ["traducir"] and len(a) == 2:
        d = leer_antes()
        if not d:
            print("Raids: ERROR, no hay datos/raids.json todavía")
            sys.exit(1)
        nuevas = json.load(open(a[1], encoding="utf-8"))
        tr = dict(d.get("traducciones") or {})
        tr.update({k: v.strip() for k, v in nuevas.items() if isinstance(v, str) and v.strip()})
        pend = traducir_doc(d, tr)
        escribir(d)
        print("Raids: traducciones guardadas en datos/raids.json (CAMBIA)" + pendientes_txt(pend))
        return
    carpeta = a[1] if a[:1] == ["--html"] and len(a) == 2 else None
    avisos = []
    try:
        man = json.loads(get(LD + "/raids/manifest.json", carpeta))
    except ValueError:
        print("Raids: ERROR, no se puede leer el índice de Leek Duck; no se toca el JSON")
        sys.exit(1)
    ahora = datetime.now(TZ)
    rots = []
    for clave, tipo in (("regular_raids", "normal"), ("shadow_raids", "oscura")):
        for r in man.get(clave) or []:
            try:
                ini, fin = hora(r["start_date"], r.get("local_time", True)), hora(r["end_date"], r.get("local_time", True))
            except (KeyError, ValueError):
                avisos.append("fechas raras en " + str(r.get("slug")))
                continue
            if fin <= ahora or ini > ahora + timedelta(days=DIAS_VISTA):
                continue
            h = get(LD + "/raids/%s.html" % r["slug"], carpeta)
            nv = niveles(h, tipo == "oscura", carpeta, avisos)
            if not nv:
                avisos.append("rotación sin jefes: " + r["slug"])
                continue
            rots.append({"tipo": tipo, "titulo_en": tx(r.get("title", "")), "inicio": ini.isoformat(), "fin": fin.isoformat(),
                         "niveles": nv})
    rots.sort(key=lambda r: (r["inicio"], r["tipo"]))
    jefes = [j for r in rots for n in r["niveles"] for j in n["jefes"]]
    con = [j for j in jefes if j["counters"]]
    ok = rots and jefes and len(con) >= 0.7 * len(jefes)
    if not ok:
        print("Raids: ERROR, no se han podido leer bien los jefes o sus counters; no se toca el JSON")
        for x in avisos:
            print("  aviso: " + x)
        sys.exit(1)
    antes = leer_antes()
    d = {"fuente": "Leek Duck (jefes) · Pokémon GO Hub (counters)", "url": LD + "/raid-bosses/", "rotaciones": rots}
    pend = traducir_doc(d, (antes or {}).get("traducciones") or {})
    estado = "IGUAL" if antes == d else "CAMBIA"
    if estado == "CAMBIA":
        escribir(d)
    print("Raids: OK %d rotaciones, %d jefes (%d con counters) (%s)%s" % (len(rots), len(jefes), len(con), estado, pendientes_txt(pend)))
    for x in avisos:
        print("  aviso: " + x)


if __name__ == "__main__":
    main()
