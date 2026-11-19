#!/usr/bin/env python3
"""Actualiza los mejores atacantes de Pokémon GO desde Pokémon GO Hub (versión en español).

Uso:
    python3 scripts/actualizar_atacantes.py            # descarga las 56 páginas con curl
    python3 scripts/actualizar_atacantes.py --html DIR # usa páginas ya descargadas (DIR/raid, DIR/max y DIR/tank/*.html;
                                                       # la lista general, en DIR/raid/general.html y DIR/tank/general.html;
                                                       # las clasificaciones sin legado, en DIR/<modo>/api_<tipo>_<con|sin>.json)

A cada atacante que necesita una MT élite le añade "sin_legado": su mejor combinación sin ataques de legado (API de
Pokémon GO Hub con «Permitir ataques de legado» desactivado) y el % que conserva; null si así ya no está en la lista.

Escribe datos/atacantes-incursiones.json, datos/atacantes-max.json y datos/tanques-max.json SOLO si la página se ha leído bien,
y dice si los datos han cambiado respecto a los que ya había (IGUAL / CAMBIA). Sale con código 1 si algo falla.
"""
import html, json, os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIPOS = [("normal", "Normal"), ("fighting", "Lucha"), ("flying", "Volador"), ("poison", "Veneno"), ("ground", "Tierra"),
         ("rock", "Roca"), ("bug", "Bicho"), ("ghost", "Fantasma"), ("steel", "Acero"), ("fire", "Fuego"), ("water", "Agua"),
         ("grass", "Planta"), ("electric", "Eléctrico"), ("psychic", "Psíquico"), ("ice", "Hielo"), ("dragon", "Dragón"),
         ("dark", "Siniestro"), ("fairy", "Hada")]
URLS = {"raid": "https://db.pokemongohub.net/es/pokemon-list/best-per-type/",
        "max": "https://db.pokemongohub.net/es/pokemon-list/best-dynamax-per-type/",
        "tank": "https://db.pokemongohub.net/es/pokemon-list/best-dynamax-tanks-per-type/"}
SALIDA = {"raid": "datos/atacantes-incursiones.json", "max": "datos/atacantes-max.json", "tank": "datos/tanques-max.json"}
# Clasificación general (todos los tipos juntos). Para Combates Max, Pokémon GO Hub no tiene: la página la saca de las listas por tipo.
GENERAL = {"raid": "https://db.pokemongohub.net/es/best/overall-attackers",
           "tank": "https://db.pokemongohub.net/es/best-dyanamax-tanks"}
WEB = {"raid": "https://db.pokemongohub.net/es/pokemon-list/best-per-type",
       "max": "https://db.pokemongohub.net/es/best/dynamax-attackers-per-type",
       "tank": "https://db.pokemongohub.net/es/best/dynamax-tanks-per-type"}
MESES = {"ene": 1, "jan": 1, "feb": 2, "mar": 3, "abr": 4, "apr": 4, "may": 5, "jun": 6, "jul": 7, "ago": 8, "aug": 8,
         "sep": 9, "oct": 10, "nov": 11, "dic": 12, "dec": 12}


def tx(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def cell(tr, c):
    m = re.search(r'<td[^>]*data-column-id="%s"[^>]*>(.*?)</td>' % c, tr, re.S)
    return m.group(1) if m else ""


def mv(c):
    n = re.search(r"<span[^>]*>([^<]+)</span>", c)
    n = html.unescape(n.group(1)).strip() if n else tx(c)
    return {"nombre": n.rstrip("+").strip(), "legado": "Movimiento de legado" in c, "plus": n.endswith("+")}


def num(s):
    try:
        return float(re.sub(r"[^0-9.]", "", s.replace(".", "").replace(",", ".")))
    except ValueError:
        return None


def fecha(x):
    m = re.match(r"(\d+) (\w+)\.? (\d{4}), (\d+):(\d+)", x or "")
    return (int(m[3]), MESES.get(m[2][:3].lower(), 0), int(m[1]), int(m[4]), int(m[5])) if m else (0,)


def filas(h):
    for tr in re.findall(r"<tr>(.*?)</tr>", h, re.S):
        if re.search(r'<td[^>]*data-column-id="attacker_name"', tr):
            yield tr


def nombre_de(a):
    nm = re.search(r'data-pokemon-chip-name="true">([^<]+)<', a)
    return html.unescape(nm.group(1)).strip() if nm else tx(a)


def icono_de(a):
    """Icono del juego (pm384.fMEGA, pm103.fALOLA…) a partir de la imagen de Pokémon GO Hub (384-mega.webp).
    Oscuro y Dinamax usan el mismo icono que el normal; la agenda busca el icono en su hoja de iconos."""
    m = re.search(r"(?:%2F|/)images(?:%2F|/)pokemon(?:%2F|/)([a-z0-9-]+)\.webp", a)
    if not m or not m.group(1).split("-")[0].isdigit():
        return ""
    p = m.group(1).split("-")
    resto = [x for x in p[1:] if x not in ("shadow", "dynamax", "purified")]
    return "pm" + p[0] + (".f" + "_".join(resto).upper() if resto else "")


def iconos_pagina(h):
    # nombre → icono de todas las fichas de Pokémon de la página (las preguntas frecuentes no traen imagen)
    d = {}
    for a in re.findall(r'<a[^>]*data-pokemon-chip="true".*?</a>', h, re.S):
        n, i = nombre_de(a), icono_de(a)
        if n and i:
            d.setdefault(n, i)
    return d


def incursiones(h):
    F, tier = [], ""
    for tr in filas(h):
        t = re.search(r'data-tier="([A-Z+]+)"', cell(tr, "tier"))
        if t:
            tier = t.group(1)
        o = re.sub(r"\D", "", tx(cell(tr, "order")))
        a = cell(tr, "attacker_name")
        F.append({"puesto": int(o) if o else len(F) + 1, "tier": tier, "nombre": nombre_de(a), "icono": icono_de(a),
                  "rapido": mv(cell(tr, "qm_name")), "cargado": mv(cell(tr, "cm_name")), "edps": num(tx(cell(tr, "score")))})
        if len(F) >= 10:
            break
    top = F[0]["edps"] if F and F[0]["edps"] else None
    for f in F:
        f["pct"] = round(100 * f["edps"] / top) if top and f["edps"] else None
    P = []  # tarjetas destacadas: General, Mega / Primigenio, Oscuro, Alternativa no legendaria, Sin MT élite
    for lab, body in re.findall(r'<article[^>]*>\s*<span[^>]*>([^<]+)</span>\s*(<a[^>]*data-pokemon-chip="true".*?)</article>', h, re.S):
        ms = [m for m in re.split(r'(?=<a [^>]*title="Opens )', body.split("</a>", 1)[-1]) if re.match(r'<a [^>]*title="Opens ', m)]
        ed = re.search(r"eDPS.*?<dd[^>]*>([^<]+)</dd>", body, re.S)
        if len(ms) < 2 or 'data-pokemon-chip-name="true"' not in body:
            continue
        d = {"etiqueta": html.unescape(lab).strip(), "nombre": nombre_de(body), "icono": icono_de(body.split("</a>", 1)[0]),
             "rapido": mv(ms[0]), "cargado": mv(ms[1]),
             "edps": num(ed.group(1)) if ed else None}
        if top and d["edps"]:
            d["pct"] = round(100 * d["edps"] / top)
        if d not in P:
            P.append(d)
    return F, P


def forma(nombre, href=""):
    # Gigamax / Dinamax según el nombre y el enlace; las formas coronadas y Eternatus tienen un ataque Max propio
    n = nombre.lower()
    if "gigamax" in n or "gigantamax" in href.lower():
        return "Gigamax"
    if "dinamax" in n or "dynamax" in href.lower():
        return "Dinamax"
    return "Especial"


def combates_max(h, es):
    F, tier = [], ""
    for tr in filas(h):
        t = re.search(r'data-tier="([A-Z+]+)"', cell(tr, "tier"))
        if t:
            tier = t.group(1)
        a = cell(tr, "attacker_name")
        href = (re.search(r'href="([^"]+)"', a) or [None, ""])[1]
        nombre = nombre_de(a)
        q = cell(tr, "qm_name")
        o = re.sub(r"\D", "", tx(cell(tr, "order")))
        dmg = re.sub(r"\D", "", tx(cell(tr, "dynamax_maxMoveDamage")))
        F.append({"puesto": int(o) if o else len(F) + 1, "tier": tier, "nombre": nombre, "icono": icono_de(a), "forma": forma(nombre, href),
                  "rapido": {"nombre": tx(re.sub(r"<button.*?</button>", "", q, flags=re.S)).rstrip("+").strip(),
                             "legado": "Movimiento de legado" in q},
                  "max": tx(cell(tr, "cm_name")), "dano": int(dmg) if dmg else None})
        if len(F) >= 10:
            break
    top = F[0]["dano"] if F and F[0]["dano"] else None
    for f in F:
        f["pct"] = round(100 * f["dano"] / top) if top and f["dano"] else None
    texto = tx(re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", h))
    P, ico = [], iconos_pagina(h)  # preguntas frecuentes de la fuente: mejor sin Gigamax y mejor sin MT élite
    for etiqueta, clave in (("Sin Gigamax", "sin Gigamax"), ("Sin MT élite", "sin una MT élite")):
        m = re.search(r"¿Cuál es el mejor atacante de tipo " + re.escape(es) + " " + re.escape(clave) +
                      r"\? (.+?) es la mejor opción, con (\d+) de daño por ataque Max.*? Llévalo con (.+?) como ataque rápido y (.+?) como ataque Max", texto)
        if not m:
            continue
        d = {"etiqueta": etiqueta, "nombre": m.group(1).strip(), "icono": ico.get(m.group(1).strip(), ""), "forma": forma(m.group(1)),
             "rapido": {"nombre": m.group(3).strip(), "legado": False}, "max": m.group(4).strip(), "dano": int(m.group(2)),
             "pct": round(100 * int(m.group(2)) / top) if top else None}
        igual = [r for r in F if r["nombre"] == d["nombre"] and r["rapido"]["nombre"] == d["rapido"]["nombre"] and r["max"] == d["max"]]
        if igual:
            d["forma"], d["rapido"]["legado"], d["icono"] = igual[0]["forma"], igual[0]["rapido"]["legado"], igual[0]["icono"]
        P.append(d)
    return F, P


def tanques(h):
    # Tanques de Combates Max contra ataques de un tipo: puntuación (100 = Blissey Dinamax, el mejor tanque general)
    # y PS que pierde de media por golpe del jefe de referencia
    F, tier = [], ""
    for tr in filas(h):
        t = re.search(r'data-tier="([A-Z+]+)"', cell(tr, "tier")) or re.match(r"\s*([A-Z+]{1,3})\s*$", tx(cell(tr, "tier")))
        if t:
            tier = t.group(1)
        a = cell(tr, "attacker_name")
        href = (re.search(r'href="([^"]+)"', a) or [None, ""])[1]
        nombre = nombre_de(a)
        q = cell(tr, "qm_name")
        o = re.sub(r"\D", "", tx(cell(tr, "order")))
        F.append({"puesto": int(o) if o else len(F) + 1, "tier": tier, "nombre": nombre, "icono": icono_de(a), "forma": forma(nombre, href),
                  "rapido": {"nombre": tx(re.sub(r"<button.*?</button>", "", q, flags=re.S)).rstrip("*+").strip(),
                             "legado": "Movimiento de legado" in q or tx(q).endswith("*")},
                  "puntuacion": num(tx(cell(tr, "score"))), "ps": num(tx(cell(tr, "incomingHPPercent")))})
        if len(F) >= 10:
            break
    top = F[0]["puntuacion"] if F and F[0]["puntuacion"] else None
    for f in F:
        f["pct"] = round(100 * f["puntuacion"] / top) if top and f["puntuacion"] else None
    return F, []


API = "https://db.pokemongohub.net/api/counters?view=ranking"
# Rival neutro con el que Pokémon GO Hub hace sus listas por tipo (el mismo que usa su web)
NEUTRO = {"maxCP": 5000, "atk": 200, "def": 180, "sta": 200, "id": 0, "name": "BOB", "pokemonId": "BOB", "type1": "normal",
          "form": None, "formId": "", "template_id": "BOB_THE_DEFENDER"}


def cuerpo_api(modo, tipo, legado):
    """La misma clasificación por tipo de Pokémon GO Hub, con o sin ataques de legado («Permitir ataques de legado»)."""
    dmax = modo == "max"
    return {"target": NEUTRO, "locale": "es", "targetRaidLevel": "DYNAMAX_TIER_5" if dmax else "5", "weather": "extreme",
            "responseSize": 400, "attackerCPMinimum": 0, "includePrimalPokemon": not dmax, "includeShadowPokemon": not dmax,
            "includeMegaPokemon": not dmax, "includeUnavailablePokemon": False, "megaLevel": 1, "rankForType": tipo,
            "allowLegacyMoves": legado, "allowMixedMovesets": True, "allowOfftypeAttackers": True,
            "allowOnlyDynamaxEligiblePokémon": dmax}


def leer_api(carpeta, tipo, legado):
    try:
        with open(os.path.join(carpeta, "api_%s_%s.json" % (tipo, "con" if legado else "sin")), encoding="utf-8") as f:
            at = json.load(f)["attackers"]
        lista = [(x["attacker"]["name"].strip(), x["qm"]["name"].strip(), x["cm"]["name"].strip(), float(x["score"]),
                  bool(x["qm"]["isLegacy"] or x["cm"]["isLegacy"])) for x in at]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if len(lista) < 5 or (not legado and any(x[4] for x in lista)):
        return None  # respuesta rara, o la API no ha hecho caso a la opción
    return lista


FORMA_ICONO = {"Mega": "MEGA", "Mega X": "MEGA_X", "Mega Y": "MEGA_Y", "Primal": "PRIMAL", "Gigantamax": "GIGANTAMAX",
               "Alola": "ALOLA", "Galarian": "GALARIAN", "Hisuian": "HISUIAN", "Paldea": "PALDEA"}
N_TODOS = 3  # puestos que se guardan de cada Pokémon: sus mejores tipos


def clasificacion(h):
    """La clasificación completa de un tipo que trae la página de Pokémon GO Hub (los mismos datos de su lista)."""
    h = h.replace('\\"', '"')
    i = h.find('"initialData":{"attackers":')
    if i < 0:
        return []
    try:
        lista = json.JSONDecoder().raw_decode(h[h.find("[", i):].replace("\\\\", "\\"))[0]
    except ValueError:
        return []

    def ref(v, n=0):
        """La página repite objetos con referencias ("$73:props:initialData:attackers:5:cm"): se resuelven aquí."""
        m = re.match(r"\$[0-9a-f]+:props:initialData:(.+)$", v) if isinstance(v, str) else None
        if not m or n > 5:
            return v
        o = {"attackers": lista}
        for k in m.group(1).split(":"):
            o = o[int(k)] if isinstance(o, list) else o[k]
        return ref(o, n + 1)
    try:
        for x in lista:
            for k in ("attacker", "qm", "cm"):
                x[k] = ref(x[k])
    except (KeyError, IndexError, ValueError, TypeError):
        return []

    def bien(x):
        try:
            return bool(x["attacker"]["name"] and x["qm"]["name"] and x["cm"]["name"] and float(x["score"]) > 0)
        except (KeyError, TypeError, ValueError):
            return False
    return [x for x in lista if isinstance(x, dict) and bien(x)]


def poner_todos(out, carpeta, modo):
    """Para el buscador: todos los Pokémon de las clasificaciones por tipo (400 por tipo en incursiones; todos los
    disponibles en Combates Max), cada uno con sus mejores tipos: puesto, ataques y % del n.º 1 de ese tipo."""
    por = {}
    for slug, _ in TIPOS:
        h = open(os.path.join(carpeta, slug + ".html"), encoding="utf-8", errors="replace").read()
        lista = clasificacion(h)
        if not lista:
            return False
        mejor = float(lista[0]["score"])
        for x in lista:
            a = x["attacker"]
            forma = (a.get("form") or "").replace(" Shadow", "").replace("Shadow", "").strip()
            f = FORMA_ICONO.get(forma, "")
            p = por.setdefault(a["name"].strip(), {"nombre": a["name"].strip(), "icono": "pm%d" % a["id"] + (".f" + f if f else ""),
                                                   "puestos": []})
            pct = round(float(x["score"]) / mejor * 100) if mejor else None
            p["puestos"].append([slug, int(x["order"]), x["qm"]["name"].strip(), bool(x["qm"]["isLegacy"]),
                                 x["cm"]["name"].strip(), bool(x["cm"]["isLegacy"]), pct])
    for p in por.values():
        p["puestos"] = sorted(p["puestos"], key=lambda r: (-(r[6] or 0), r[1]))[:N_TODOS]
    lista = sorted(por.values(), key=lambda p: (-(p["puestos"][0][6] or 0), p["nombre"]))
    # Compacto (un documento de la base de datos no puede pasar de 256 KB): los ataques van en una lista aparte y cada
    # puesto es [tipo, puesto, rápido, cargado, legado, %] con el índice del ataque y legado = 1 rápido + 2 cargado
    ataques = sorted({r[2] for p in lista for r in p["puestos"]} | {r[4] for p in lista for r in p["puestos"]})
    i = {a: n for n, a in enumerate(ataques)}
    out["todos"] = {"ataques": ataques, "pokemon": [
        [p["nombre"], p["icono"], [[r[0], r[1], i[r[2]], i[r[4]], (1 if r[3] else 0) + (2 if r[5] else 0), r[6]] for r in p["puestos"]]]
        for p in lista]}
    return len(lista) >= 100


def poner_sin_legado(out, carpeta, modo):
    """Añade "sin_legado" a cada Pokémon que necesita un ataque de legado (MT élite): su mejor combinación sin ataques de
    legado y qué % conserva de lo que hace con el de legado, las dos cosas de la misma simulación de Pokémon GO Hub.
    null si sin ataques de legado ya no está en la clasificación de ese tipo."""
    base = lambda m: (m or "").rstrip("+").strip()
    api = {t: (leer_api(carpeta, t, True), leer_api(carpeta, t, False)) for t, _ in TIPOS}

    def buscar(lista, fila, exacto):
        for x in lista or []:
            if x[0] == fila["nombre"] and (not exacto or (base(x[1]) == fila["rapido"]["nombre"] and
                                                         (modo == "max" or base(x[2]) == fila["cargado"]["nombre"]))):
                return x
        return None

    def poner(fila, tipos):
        if not (fila["rapido"]["legado"] or (modo == "raid" and fila["cargado"]["legado"])):
            return
        for t in tipos:
            con, sin = api[t]
            c = con and sin and (buscar(con, fila, True) or (len(tipos) == 1 and buscar(con, fila, False)))
            if c:
                alt = buscar(sin, fila, False)
                fila["sin_legado"] = None if not alt else dict(
                    {"rapido": {"nombre": base(alt[1]), "plus": alt[1].endswith("+")}, "pct": round(alt[3] / c[3] * 100)},
                    **({} if modo == "max" else {"cargado": {"nombre": base(alt[2]), "plus": alt[2].endswith("+")}}))
                return

    for t in out["tipos"]:
        for fila in t["top"] + t["destacados"]:
            poner(fila, [t["id"]])
    for fila in (out.get("general") or {}).get("top", []):
        poner(fila, [t for t, _ in TIPOS])


def procesar(modo, carpeta):
    out = {"fuente": "Pokémon GO Hub (db.pokemongohub.net)", "tipos": []}
    for slug, es in TIPOS:
        h = open(os.path.join(carpeta, slug + ".html"), encoding="utf-8", errors="replace").read()
        u = re.search(r"Actualizado el (\d+ \w+\.? \d{4}, \d+:\d+ UTC)", h)
        top, dest = incursiones(h) if modo == "raid" else combates_max(h, es) if modo == "max" else tanques(h)
        out["tipos"].append({"id": slug, "nombre": es, "actualizado": u.group(1) if u else "", "top": top, "destacados": dest})
    out["actualizado"] = max((t["actualizado"] for t in out["tipos"]), key=fecha, default="")
    out["url"] = WEB[modo]
    if modo in GENERAL:
        h = open(os.path.join(carpeta, "general.html"), encoding="utf-8", errors="replace").read()
        u = re.search(r"Actualizado el (\d+ \w+\.? \d{4}, \d+:\d+ UTC)", h)
        top = incursiones(h)[0] if modo == "raid" else tanques(h)[0]
        out["general"] = {"actualizado": u.group(1) if u else "", "url": GENERAL[modo], "top": top}
        campo = "edps" if modo == "raid" else "puntuacion"
        if not (len(top) == 10 and all(r["nombre"] and r[campo] and r["rapido"]["nombre"] for r in top)):
            return None
    if modo in ("raid", "max"):
        poner_sin_legado(out, carpeta, modo)
        if not poner_todos(out, carpeta, modo):
            out.pop("todos", None)  # sin la clasificación completa, el buscador usa solo las listas
    if modo == "tank":  # 10 por tipo, con puntuación y PS por golpe
        ok = len(out["tipos"]) == 18 and all(len(t["top"]) == 10 and all(r["nombre"] and r["puntuacion"] and r["ps"] and r["rapido"]["nombre"]
                                                                          for r in t["top"]) for t in out["tipos"])
    elif modo == "raid":  # 10 por tipo, con nombre y eDPS
        ok = len(out["tipos"]) == 18 and all(len(t["top"]) == 10 and all(r["nombre"] and r["edps"] for r in t["top"]) for t in out["tipos"])
    else:  # algunos tipos tienen menos de 10 disponibles (p. ej. Veneno)
        ok = len(out["tipos"]) == 18 and all(t["top"] and all(r["nombre"] and r["dano"] and r["max"] for r in t["top"]) for t in out["tipos"]) \
            and sum(len(t["top"]) for t in out["tipos"]) >= 150
    return out if ok else None


def descargar(destino):
    for modo, base in URLS.items():
        os.makedirs(os.path.join(destino, modo), exist_ok=True)
        for slug, _ in TIPOS:
            subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", "--retry", "2", "-o", os.path.join(destino, modo, slug + ".html"), base + slug], check=False)
        if modo in GENERAL:
            subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", "--retry", "2", "-o", os.path.join(destino, modo, "general.html"), GENERAL[modo]], check=False)
        if modo in ("raid", "max"):  # clasificaciones con y sin ataques de legado (para «sin MT élite»)
            for slug, _ in TIPOS:
                for leg in (True, False):
                    subprocess.run(["curl", "-s", "-A", "Mozilla/5.0", "--retry", "2", "--max-time", "60", "-H", "content-type: application/json",
                                    "-X", "POST", API, "-d", json.dumps(cuerpo_api(modo, slug, leg)),
                                    "-o", os.path.join(destino, modo, "api_%s_%s.json" % (slug, "con" if leg else "sin"))], check=False)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--html":
        carpeta = sys.argv[2]
    else:
        carpeta = tempfile.mkdtemp(prefix="hub-")
        descargar(carpeta)
    fallo = False
    for modo, nombre in (("raid", "Incursiones"), ("max", "Combates Max"), ("tank", "Tanques Max")):
        try:
            datos = procesar(modo, os.path.join(carpeta, modo))
        except OSError as e:
            datos = None
            print(nombre + ": ERROR al leer las páginas:", e)
        if not datos:
            print(nombre + ": ERROR, la página ha cambiado de formato; no se toca el JSON")
            fallo = True
            continue
        ruta = os.path.join(ROOT, SALIDA[modo])
        antes = None
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                antes = json.load(f)
        estado = "IGUAL" if antes == datos else "CAMBIA"
        if estado == "CAMBIA":
            os.makedirs(os.path.dirname(ruta), exist_ok=True)
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(datos, f, ensure_ascii=False, indent=1)
                f.write("\n")
        print("%s: OK %d filas, %d destacados, datos del %s (%s)" % (
            nombre, sum(len(t["top"]) for t in datos["tipos"]), sum(len(t["destacados"]) for t in datos["tipos"]), datos["actualizado"], estado))
    sys.exit(1 if fallo else 0)


if __name__ == "__main__":
    main()
