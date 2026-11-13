#!/usr/bin/env python3
"""Eventos de la agenda de Pokémon GO (documento agenda/snapshot de la base de datos de la agenda).

La agenda NO depende de Google Calendar: lee este documento. Antes, guarda el documento con
ArtifactData get (out_dir /tmp/hub/db): queda en db/agenda/snapshot.json. Se trabaja sobre
datos/agenda.json (se copia solo la primera vez).

Uso (desde /tmp/hub):
  python3 scripts/agenda.py ver               # lista numerada de los eventos (hora de España)
  python3 scripts/agenda.py ver N             # un evento entero: título, horas y descripción
  python3 scripts/agenda.py poner EV.json …   # añade o sustituye eventos (un objeto o una lista por archivo)
  python3 scripts/agenda.py quitar N          # borra el evento N (p. ej. si se ha cancelado)
  python3 scripts/agenda.py guardar           # quita los terminados, ordena y dice IGUAL / CAMBIA

Cada evento de EV.json:
  {"titulo": "Pokémon GO: Hora Destacada – Noibat · ×2 Caramelos",
   "inicio": "2026-11-26 18:00", "fin": "2026-11-26 19:00",          (hora de España)
   "descripcion": "<b>🎁 Bonificaciones:</b> …<br><br>…<br><br>🔗 <a href=\\"URL\\">Ver noticia</a>",
   "sustituye": "título exacto de un evento viejo"}                    (opcional)
Un evento sustituye a otro si empieza el mismo día y es del mismo tipo (lo que va antes de " – " o
" · " en el título; así "Lunes Max – Pokémon por anunciar" pasa a "Lunes Max – Cryogonal"), o si
"sustituye" es el título exacto del viejo.
"""
import json, os, re, sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Madrid")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGEN = os.path.join(ROOT, "db", "agenda", "snapshot.json")
TRABAJO = os.path.join(ROOT, "datos", "agenda.json")
ETIQUETAS = {"🎁 Bonificaciones:", "🎟️ Pases gratis:", "🎫 GO Pass gratis:", "⚔️ Incursiones:",
             "🎯 ¿Vale la pena?:", "💳 De pago:", "💡 ¿Merece la pena?:"}
DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]


def fallo(msg):
    print("ERROR: " + msg)
    sys.exit(1)


def leer_json(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def cargar():
    if not os.path.exists(TRABAJO):
        if not os.path.exists(ORIGEN):
            fallo("no está " + ORIGEN + ": léelo antes con ArtifactData get (collection \"agenda\", doc_id \"snapshot\", out_dir \"/tmp/hub/db\")")
        os.makedirs(os.path.dirname(TRABAJO), exist_ok=True)
        escribir(leer_json(ORIGEN))
    return leer_json(TRABAJO)


def escribir(doc):
    doc["events"].sort(key=lambda e: (cuando(e, "start"), e.get("summary", "")))
    with open(TRABAJO, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
        f.write("\n")


def cuando(e, campo):
    w = e.get(campo) or {}
    if w.get("dateTime"):
        return datetime.fromisoformat(w["dateTime"].replace("Z", "+00:00")).astimezone(TZ)
    if w.get("date"):
        return datetime.fromisoformat(w["date"]).replace(tzinfo=TZ)
    return datetime(1970, 1, 1, tzinfo=TZ)


def hoy0():
    return datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)


def tipo(titulo):
    t = re.sub(r"^pok[eé]mon go\s*:\s*", "", titulo.strip(), flags=re.I)
    return re.split(r"\s+[–—·-]\s+", t, maxsplit=1)[0].strip().lower()


def bonito(e):
    a, b = cuando(e, "start"), cuando(e, "end")
    ini = "%s %s %s" % (DIAS[a.weekday()], a.strftime("%d/%m"), a.strftime("%H:%M"))
    fin = b.strftime("%H:%M") if a.date() == b.date() else "%s %s %s" % (DIAS[b.weekday()], b.strftime("%d/%m"), b.strftime("%H:%M"))
    return ini + "–" + fin if a.date() == b.date() else ini + " → " + fin


def hora(s, campo):
    if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}", s.strip()):
        fallo('"%s" tiene que ser "AAAA-MM-DD HH:MM" (hora de España), no %r' % (campo, s))
    return datetime.strptime(s.strip().replace("T", " "), "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


def evento(x, archivo):
    if not isinstance(x, dict):
        fallo(archivo + ": cada evento tiene que ser un objeto {titulo, inicio, fin, descripcion}")
    tit, desc = x.get("titulo"), x.get("descripcion", "")
    if not isinstance(tit, str) or not tit.startswith("Pokémon GO: ") or "\n" in tit or len(tit) > 200:
        fallo('%s: "titulo" tiene que empezar por "Pokémon GO: " y ser una sola línea' % archivo)
    if not isinstance(desc, str) or len(desc) > 6000:
        fallo('%s: "descripcion" tiene que ser texto (HTML) de menos de 6000 caracteres' % archivo)
    if re.search(r"\$|\bUSD\b", desc):
        fallo("%s: hay un precio en dólares; los precios van SIEMPRE en euros (tabla del Paso 4)" % archivo)
    a, b = hora(x.get("inicio"), "inicio"), hora(x.get("fin"), "fin")
    if b <= a:
        fallo("%s: el fin tiene que ser después del inicio" % archivo)
    if b < hoy0():
        fallo("%s: ese evento ya ha terminado" % archivo)
    for et in re.findall(r"<b>(.*?)</b>", desc):
        if et.strip() not in ETIQUETAS:
            print("AVISO: etiqueta desconocida <b>%s</b> en %s (la agenda solo entiende las del Paso 4)" % (et, tit))
    if "🔗" not in desc:
        print("AVISO: %s no tiene el enlace \"🔗 Ver noticia\"" % tit)
    sus = x.get("sustituye")
    return {"summary": tit, "start": {"dateTime": a.isoformat(), "date": None},
            "end": {"dateTime": b.isoformat(), "date": None}, "description": desc}, sus if isinstance(sus, str) else None


def poner(archivos):
    doc = cargar()
    for arch in archivos:
        try:
            datos = leer_json(arch)
        except json.JSONDecodeError as err:
            fallo('%s no es JSON válido (línea %d, columna %d): revisa las comillas; dentro del texto van como \\" (p. ej. <a href=\\"URL\\">)'
                  % (arch, err.lineno, err.colno))
        for x in datos if isinstance(datos, list) else [datos]:
            nuevo, sus = evento(x, arch)
            dia, tp = cuando(nuevo, "start").date(), tipo(nuevo["summary"])
            igual = [i for i, e in enumerate(doc["events"])
                     if (sus and e.get("summary") == sus) or (cuando(e, "start").date() == dia and tipo(e.get("summary", "")) == tp)]
            if len(igual) > 1:
                fallo("%s coincide con varios eventos: %s. Usa \"sustituye\" con el título exacto o quita uno con «quitar N»"
                      % (nuevo["summary"], " | ".join(doc["events"][i]["summary"] for i in igual)))
            if igual:
                viejo = doc["events"][igual[0]]
                if viejo == nuevo:
                    print("SIN CAMBIOS: " + nuevo["summary"])
                    continue
                doc["events"][igual[0]] = nuevo
                print("SUSTITUIDO: %s  (antes: %s)" % (nuevo["summary"], viejo.get("summary")))
            else:
                doc["events"].append(nuevo)
                print("AÑADIDO: %s · %s" % (nuevo["summary"], bonito(nuevo)))
            escribir(doc)


def ver(n=None):
    doc = cargar()
    ev = doc["events"]
    if n is not None:
        if not n.isdigit() or not 1 <= int(n) <= len(ev):
            fallo("no hay evento %s; mira la lista con «ver»" % n)
        e = ev[int(n) - 1]
        print("Título: %s\nCuándo: %s\nDescripción:\n%s" % (e.get("summary"), bonito(e), e.get("description", "")))
        return
    h = hoy0()
    for i, e in enumerate(ev, 1):
        print("%2d. %s · %s%s" % (i, bonito(e), e.get("summary"), "  (terminado)" if cuando(e, "end") < h else ""))
    print("%d eventos" % len(ev))


def quitar(n):
    doc = cargar()
    if not n.isdigit() or not 1 <= int(n) <= len(doc["events"]):
        fallo("no hay evento %s; mira la lista con «ver»" % n)
    e = doc["events"].pop(int(n) - 1)
    escribir(doc)
    print("QUITADO: " + e.get("summary", ""))


def guardar():
    doc = cargar()
    h = hoy0()
    fuera = [e for e in doc["events"] if cuando(e, "end") < h]
    doc["events"] = [e for e in doc["events"] if cuando(e, "end") >= h and str(e.get("summary", "")).startswith("Pokémon GO")]
    antes = leer_json(ORIGEN).get("events") if os.path.exists(ORIGEN) else None
    estado = "IGUAL" if antes == sorted(doc["events"], key=lambda e: (cuando(e, "start"), e.get("summary", ""))) else "CAMBIA"
    doc["updatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    escribir(doc)
    print("Agenda: %d eventos, %d terminados quitados (%s)%s" % (len(doc["events"]), len(fuera), estado,
          ": guárdala con ArtifactData set (collection \"agenda\", doc_id \"snapshot\", file_path \"%s\")" % TRABAJO if estado == "CAMBIA" else ""))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["ver"] and len(a) <= 2:
        ver(a[1] if len(a) == 2 else None)
    elif a[:1] == ["poner"] and len(a) >= 2:
        poner(a[1:])
    elif a[:1] == ["quitar"] and len(a) == 2:
        quitar(a[1])
    elif a == ["guardar"]:
        guardar()
    else:
        print(__doc__)
        sys.exit(2)
