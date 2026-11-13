#!/usr/bin/env python3
"""Convierte los eventos "Pokémon GO:" de la agenda (su documento agenda/snapshot) en datos/eventos.json.

Uso:
    python3 scripts/eventos_json.py <copia.json>

<copia.json> es el documento agenda/snapshot de la agenda visual: {"events": [{"summary", "start", "end", "description"}], "updatedAt"}.
Saca de cada descripción las mismas líneas que lee la agenda: 🎁 Bonificaciones, 🎟️ Pases gratis, 🎫 GO Pass gratis,
⚔️ Incursiones, 💳 De pago y 💡 ¿Merece la pena?, más el texto y el enlace a la noticia. Solo reescribe el JSON si cambia algo.
"""
import html, json, os, re, sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SALIDA = os.path.join(ROOT, "datos", "eventos.json")
BR = r"(?:<br\s*/?>\s*)*"
BONUS = re.compile(r"(?:<b>\s*)?(?:🎁\s*)?Bonificaciones:\s*(?:</b>)?\s*([^<]*)" + BR, re.I)
PASES = re.compile(r"(?:<b>\s*)?(?:🎟️?\s*)?Pases(?: de incursi[oó]n)?(?: gratis)?:\s*(?:</b>)?\s*([^<]*)" + BR, re.I)
GOPASS = re.compile(r"(?:<b>\s*)?(?:🎫\s*)?GO Pass gratis:\s*(?:</b>)?\s*([^<]*)" + BR, re.I)
INCURSIONES = re.compile(r"(?<![A-Za-zÀ-ÿ] )(?:<b>\s*)?(?:⚔️?\s*)?Incursiones(?: y Combates Max)?:\s*(?:</b>)?\s*([^<]*)" + BR, re.I)
PAGO = re.compile(r"(?:<b>\s*)?💳\s*De pago:\s*(?:</b>)?\s*([^<]*)" + BR +
                  r"(?:(?:<b>\s*)?(?:💡\s*)?¿?Merece la pena\??:\s*(?:</b>)?\s*([^<]*))?" + BR, re.I)
TIPOS = [("Lluvia de meteoros", r"minior|meteor"), ("Hora Destacada", r"hora destacada|spotlight"),
         ("Día de la Comunidad", r"d[ií]a de la comunidad|community day"),
         ("Combates Max", r"combates? max|dinamax|dynamax|gigamax|eternatus|lunes max|max battle"), ("Incursiones", r"incursi|raid")]


def texto(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def lista(s):
    return [x.strip() for x in texto(s).split(" · ") if x.strip()]


def cuando(w):
    w = w or {}
    if w.get("dateTime"):
        return w["dateTime"], datetime.fromisoformat(w["dateTime"].replace("Z", "+00:00"))
    if w.get("date"):
        return w["date"], datetime.fromisoformat(w["date"] + "T00:00:00+01:00")
    return None, None


def tipo(nombre, ini, fin):
    t = nombre.lower()
    if re.search(TIPOS[0][1], t):
        return TIPOS[0][0]
    if ini and fin and (fin - ini >= timedelta(hours=23, minutes=59) or ini.date() != (fin - timedelta(seconds=1)).date()):
        return "Evento"
    for etiqueta, rx in TIPOS[1:]:
        if re.search(rx, t):
            return etiqueta
    return "Evento" if re.search(r"wild area|go fest|tour|safari", t) else "Especial"


def pagos(desc):
    out = []
    for que, valor in PAGO.findall(desc or ""):
        w, v = texto(que), texto(valor)
        if not w:
            continue
        # "<Nombre> (<precio>): <qué da> · …"; el nombre y el precio pueden llevar ":" (GO Pass Deluxe: X, hasta las 17:00)
        pm = re.match(r"^(.+?)\s*\(([^)]*)\)\s*:\s*(.*)$", w)
        cab, _, da = w.partition(":")
        out.append({"nombre": pm.group(1).strip() if pm else cab.strip(), "precio": pm.group(2).strip() if pm else "",
                    "da": [x.strip() for x in (pm.group(3) if pm else da).split(" · ") if x.strip()],
                    "estrellas": v.count("★"), "valoracion": re.sub(r"^[★☆\s]+[—–-]?\s*", "", v)})
    return out


def evento(e):
    resumen = re.sub(r"^pok[eé]mon go\s*:\s*", "", e.get("summary", ""), flags=re.I).strip()
    partes = resumen.split(" · ")
    s_ini, ini = cuando(e.get("start"))
    s_fin, fin = cuando(e.get("end"))
    d = e.get("description", "") or ""
    pases = texto((PASES.search(d) or [None, ""])[1])
    if re.match(r"^(no\b|gratis,?\s*no\b)", pases, re.I):
        pases = ""
    resto = PAGO.sub("", INCURSIONES.sub("", GOPASS.sub("", PASES.sub("", BONUS.sub("", d)))))
    enlace = re.search(r'<a[^>]+href="(https?://[^"]+)"', d)
    return {
        "titulo": partes[0], "tipo": tipo(partes[0], ini, fin), "inicio": s_ini, "fin": s_fin,
        "bonificaciones": lista((BONUS.search(d) or [None, ""])[1]) or partes[1:],
        "pasesGratis": pases,
        "goPassGratis": lista((GOPASS.search(d) or [None, ""])[1]),
        "incursiones": lista((INCURSIONES.search(d) or [None, ""])[1]),
        "dePago": pagos(d),
        "texto": re.sub(r"\s+", " ", texto(re.sub(r"<a\b.*?</a>", " ", resto, flags=re.S)).replace("🔗", "")).strip(),
        "noticia": html.unescape(enlace.group(1)) if enlace else None,
    }


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding="utf-8") as f:
        copia = json.load(f)
    copia = copia.get("data", copia)
    eventos = [evento(e) for e in copia.get("events", []) if re.match(r"^pok[eé]mon go\s*:", e.get("summary", ""), re.I)]
    eventos.sort(key=lambda x: x["inicio"] or "")
    datos = {"fuente": "Agenda visual (eventos «Pokémon GO:» de su base de datos)", "zonaHoraria": "Europe/Madrid",
             "copiaDeLaAgenda": copia.get("updatedAt"), "eventos": eventos}
    antes = None
    if os.path.exists(SALIDA):
        with open(SALIDA, encoding="utf-8") as f:
            antes = json.load(f)
    # La fecha de la copia cambia aunque los eventos sean los mismos: solo cuenta si cambian los eventos
    if antes and antes.get("eventos") == eventos:
        print("Eventos: %d (IGUAL)" % len(eventos))
        return
    os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
    with open(SALIDA, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("Eventos: %d (CAMBIA)" % len(eventos))


if __name__ == "__main__":
    main()
