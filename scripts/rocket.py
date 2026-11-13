#!/usr/bin/env python3
"""Equipos actuales del Team GO Rocket (Leek Duck) con las frases del juego en español de España.

Uso:
    python3 scripts/rocket.py                  # descarga leekduck.com/rocket-lineups con curl
    python3 scripts/rocket.py --html PAGINA    # usa una página ya descargada

Escribe datos/rocket.json SOLO si la página se ha leído bien y dice si ha cambiado (IGUAL / CAMBIA).
Las frases en español salen de los textos del juego (PokeMiners/pogo_assets, i18n_spanish.json).
"""
import html, json, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
URL = "https://leekduck.com/rocket-lineups/"
SALIDA = os.path.join(ROOT, "datos", "rocket.json")
TIPOS = {"normal", "fire", "water", "grass", "electric", "ice", "fighting", "poison", "ground", "flying", "psychic",
         "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy"}
# Frase en inglés (Leek Duck) → frase del juego en español (claves combat_*_quote de i18n_spanish.json)
FRASES = {
    "I will not tolerate your interference.": "No toleraré tu intromisión.",
    "My strength comes from my loyalty to Team GO Rocket.": "Mi fuerza proviene de mi lealtad al Team GO Rocket.",
    "It's time to learn your place in the world.": "Es hora de que aprendas cuál es tu lugar en el mundo.",
    "I envy you—you get to battle me!": "Te envidio, ¡tienes la oportunidad de combatir conmigo!",
    "Normal does not mean weak.": "Normal no significa débil.",
    "Do you know how hot Pokémon fire breath can get?": "¿Sabes lo caliente que puede llegar a ser el aliento de fuego de los Pokémon?",
    "These waters are treacherous!": "¡Estas aguas son traicioneras!",
    "Get ready to be shocked!": "¡Prepárate para alucinar!",
    "Don't tangle with us!": "¡No nos vaciles!",
    "You're gonna be frozen in your tracks.": "El frío puede paralizarte, ¿no lo sabes?",
    "This buff physique isn't just for show!": "Estos músculos no son solo para impresionar.",
    "Coiled and ready to strike!": "¡En posición y listo para atacar!",
    "You'll be defeated into the ground!": "¡Haré que te comas el polvo!",
    "Battle against my Flying-type Pokémon!": "¡Mis Pokémon pájaro quieren combatir contigo!",
    "Are you scared of psychics that use unseen power?": "¿Te asustan los psíquicos que usan un poder invisible?",
    "Go, my super bug Pokémon!": "¡Vamos, mi poderoso Pokémon de tipo Bicho!",
    "Let's rock and roll!": "¡Soy fuerte como una roca!",
    "Ke...ke...ke...ke...ke...ke!": "Ja, ja, ja...",
    "ROAR! ...How'd that sound?": "¡GRRR! ¿Qué te pareció eso?",
    "Wherever there is light, there is also shadow.": "Ya sé que es una frase manida, pero... Donde quiera que hay luz, también hay sombras...",
    "You're no match for my iron will!": "¡No eres rival para mi voluntad de hierro!",
    "Check out my cute Pokémon!": "¡Mira a mi Pokémon tan mono!",
    "Winning is for winners.": "Ganar es para los ganadores.",
    "Fooled ya, twerp.": "Te engañé, papanatas.",
}
FORMAS = {"Alolan": "de Alola", "Galarian": "de Galar", "Hisuian": "de Hisui", "Paldean": "de Paldea"}


def tx(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\xa0", " ")).strip()


def clave(s):
    return re.sub(r"[\s’‘'\"“”]+", " ", s).strip().lower()


FRASES_N = {clave(k): v for k, v in FRASES.items()}


def nombre_es(n):
    n = html.unescape(n).strip()
    for en, es in FORMAS.items():
        if n.startswith(en + " "):
            return n[len(en) + 1:] + " " + es
    return n


def perfil(nombre, frase_en, tipo_alt):
    """Rol, tipo y género a partir del nombre de Leek Duck ("Fire-type Female Grunt", "Cliff"...)."""
    n = nombre.lower()
    tipo = (tipo_alt or "").lower().replace(" type", "").strip()
    tipo = tipo if tipo in TIPOS else None
    genero = "chica" if "female" in n else "chico" if "male" in n else None
    if n.startswith("giovanni"):
        return {"id": "giovanni", "rol": "jefe", "nombre": "Giovanni", "tipo": None, "genero": None}
    for lider in ("cliff", "arlo", "sierra"):
        if n.startswith(lider):
            return {"id": lider, "rol": "lider", "nombre": lider.capitalize(), "tipo": None, "genero": None}
    m = re.match(r"([a-z]+)-type", n)
    if m and m.group(1) in TIPOS:
        tipo = m.group(1)
    rol = "senuelo" if "decoy" in n else "recluta"
    ident = "-".join(x for x in (rol, tipo or "sin-tipo", genero or "") if x)
    return {"id": ident, "rol": rol, "nombre": "Recluta", "tipo": tipo, "genero": genero}


def leer(h):
    upd = re.search(r'Updated on\s*<time datetime="(\d{4}-\d{2}-\d{2})', h)
    bloques = re.split(r'<div class="rocket-profile"', h)[1:]
    out = []
    for b in bloques:
        nombre = tx((re.search(r'<div class="name">(.*?)</div>', b, re.S) or [None, ""])[1])
        frase_en = tx((re.search(r'<span class="quote-text">(.*?)</span>', b, re.S) or [None, ""])[1])
        tipo_alt = (re.search(r'<span class="type"><img[^>]*alt="([^"]+)"', b) or [None, ""])[1]
        info = perfil(nombre, frase_en, tipo_alt)
        lineup = b.split('<div class="lineup-info">', 1)[-1]
        slots = []
        for trozo in re.split(r'(?=<div class="slot)', lineup)[1:]:
            cab = re.match(r'<div class="slot\s*([^"]*)"', trozo)
            num = re.search(r'<span class="number">(\d+)</span>', trozo)
            pokes = []
            for m in re.finditer(r'<span class="shadow-pokemon" data-pokemon="([^"]*)" data-type1="([^"]*)" data-type2="([^"]*)" data-double-weaknesses="([^"]*)" data-single-weaknesses="([^"]*)"', trozo):
                nm, t1, t2, dbl, sgl = m.groups()
                tipos = [t.lower() for t in (t1, t2) if t and t.lower() in TIPOS]
                # icono del juego (pm53, pm103.fALOLA…): la agenda lo busca en su hoja de iconos
                resto = trozo[m.end():].split('<span class="shadow-pokemon"', 1)[0][:1500]
                ico = re.search(r'pokemon_icons_crop/(pm\d+(?:\.f[A-Z0-9_]+)?)\.icon\.png', resto)
                pokes.append({"nombre": nombre_es(nm), "icono": ico.group(1) if ico else "", "tipos": tipos,
                              "x2": [w.lower() for w in sgl.split(",") if w.lower() in TIPOS],
                              "x4": [w.lower() for w in dbl.split(",") if w.lower() in TIPOS]})
            if num and pokes:
                slots.append({"n": int(num.group(1)), "captura": "encounter" in (cab.group(1) if cab else ""), "pokemon": pokes})
        frase = FRASES_N.get(clave(frase_en))
        info.update({"frase": frase or frase_en, "frase_en": frase_en, "frase_traducida": bool(frase), "slots": slots})
        out.append(info)
    return {"fuente": "Leek Duck (equipos) · textos del juego en español (frases)", "url": URL,
            "actualizado": upd.group(1) if upd else "", "entrenadores": out}


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--html":
        h = open(sys.argv[2], encoding="utf-8", errors="replace").read()
    else:
        r = subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", "--retry", "2", URL], capture_output=True)
        h = r.stdout.decode("utf-8", "replace")
    datos = leer(h)
    e = datos["entrenadores"]
    ids = {x["id"] for x in e}
    ok = len(e) >= 20 and {"giovanni", "cliff", "arlo", "sierra"} <= ids and all(len(x["slots"]) == 3 for x in e) \
        and all(any(s["captura"] for s in x["slots"]) for x in e if x["rol"] != "senuelo")
    if not ok:
        print("Rocket: ERROR, la página ha cambiado de formato; no se toca el JSON")
        sys.exit(1)
    antes = None
    if os.path.exists(SALIDA):
        with open(SALIDA, encoding="utf-8") as f:
            antes = json.load(f)
    estado = "IGUAL" if antes == datos else "CAMBIA"
    if estado == "CAMBIA":
        os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
        with open(SALIDA, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=1)
            f.write("\n")
    sin = [x["frase_en"] for x in e if not x["frase_traducida"]]
    print("Rocket: OK %d entrenadores, equipos del %s (%s)%s" % (len(e), datos["actualizado"], estado,
          "; frases sin traducir: " + " | ".join(sin) if sin else ""))


if __name__ == "__main__":
    main()
