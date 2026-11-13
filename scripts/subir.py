#!/usr/bin/env python3
"""Sube a GitHub los JSON de datos/ que han cambiado. Lo usan las tareas programadas de la agenda.

Uso, con el repo ya clonado:
    python3 scripts/subir.py <qué> ORIGEN=DESTINO [ORIGEN=DESTINO …]
Ejemplo:
    python3 scripts/subir.py Raids /tmp/hub/datos/raids.json=raids.json

Por cada par compara el contenido de ORIGEN con el de datos/DESTINO (sin mirar el formato ni la fecha
"updatedAt") y, si es distinto, reescribe datos/DESTINO. Si está agenda.json, vuelve a generar
datos/eventos.json. Si hay algo nuevo, lo sube a main en un commit «<qué>: actualización automática
(DD/MM/AAAA)»; si no, comprueba que se podría subir. Se salta los ORIGEN que no existen.
Termina con una línea «GitHub: …» y sale con código 1 si algo falla.
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(REPO, "datos")
AUTOR = ["-c", "user.name=Claude", "-c", "user.email=noreply@anthropic.com"]
ENTORNO = dict(os.environ, GIT_TERMINAL_PROMPT="0")


def fallo(msg):
    print("GitHub: ERROR, " + msg)
    sys.exit(1)


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def sin_fecha(d):
    return {k: v for k, v in d.items() if k != "updatedAt"} if isinstance(d, dict) else d


def ejecutar(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, env=ENTORNO, timeout=180)
    except (OSError, subprocess.TimeoutExpired) as e:
        fallo("%s: %s" % (" ".join(cmd[-4:]), e))


def git(*args):
    return ejecutar(["git", "-C", REPO, *AUTOR, *args])


def motivo(r):
    t = [x.strip() for x in (r.stderr or r.stdout or "").splitlines() if x.strip()]
    malas = [x for x in t if x.startswith(("fatal:", "error:", "remote:", "!"))]
    return (malas or t or ["código %d" % r.returncode])[0]


def main():
    a = sys.argv[1:]
    if len(a) < 2 or not all("=" in x for x in a[1:]):
        sys.exit(__doc__)
    if not os.path.exists(os.path.join(REPO, ".git")):
        fallo(REPO + " no es un repo clonado")
    for par in a[1:]:
        origen, destino = par.rsplit("=", 1)
        destino = os.path.join(DATOS, os.path.basename(destino))
        if not os.path.exists(origen):
            continue
        try:
            nuevo = leer(origen)
        except ValueError as e:
            fallo("%s no es un JSON válido (%s); no se ha subido nada" % (origen, e))
        try:
            viejo = leer(destino)
        except (OSError, ValueError):
            viejo = None
        if sin_fecha(nuevo) != sin_fecha(viejo):
            with open(destino, "w", encoding="utf-8") as f:
                json.dump(nuevo, f, ensure_ascii=False, indent=1)
                f.write("\n")
        if os.path.basename(destino) == "agenda.json":
            r = ejecutar([sys.executable, os.path.join(REPO, "scripts", "eventos_json.py"), destino])
            if r.returncode:
                fallo("eventos_json.py: " + motivo(r))
    git("add", "datos")
    cambiados = [os.path.basename(x) for x in git("diff", "--cached", "--name-only").stdout.split()]
    if not cambiados:
        r = git("push", "--dry-run", "-q", "origin", "HEAD:main")
        print("GitHub: ya estaba al día" + (" (se puede subir)" if r.returncode == 0 else "; OJO, no se podría subir: " + motivo(r)))
        return
    fecha = datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y")
    r = git("commit", "-q", "-m", "%s: actualización automática (%s)" % (a[0], fecha))
    if r.returncode:
        fallo("commit: " + motivo(r))
    r = git("push", "-q", "origin", "HEAD:main")
    if r.returncode:
        # Si alguien ha subido algo entretanto, se pone encima y se reintenta una vez
        r = git("pull", "--rebase", "-q", "origin", "main")
        if r.returncode == 0:
            r = git("push", "-q", "origin", "HEAD:main")
        if r.returncode:
            fallo("no se ha podido subir: " + motivo(r))
    print("GitHub: subido %s (%s)" % (git("rev-parse", "--short", "HEAD").stdout.strip(), ", ".join(cambiados)))


if __name__ == "__main__":
    main()
