# Guía para Claude

Proyecto personal: una agenda de Pokémon GO (una página publicada como artifact de Claude) y este repo público con sus datos en JSON. Si eres una de las tareas programadas, sigue solo las instrucciones de tu tarea: esta guía es para cuando se cambia o se amplía el proyecto.

## Reglas del dueño
- Responde siempre en español de España, breve y sin gastar tokens de más.
- La información tiene que ser exacta: solo lo confirmado por la web oficial (pokemongo.com) o por fuentes fiables (Leek Duck, Pokémon GO Hub). Nunca completes datos con suposiciones.
- Horas en hora de España (Europe/Madrid). Precios siempre en euros de la tienda web de España (store.pokemongo.com/es), nunca en dólares.
- Nombres de Pokémon, ataques y objetos como en el juego en español (textos de PokeMiners/pogo_assets, `Texts/Latest APK/JSON/i18n_spanish.json`).
- El repo es público: nada de datos personales (correo, nombre, enlaces privados). Haz los commits como Claude: `git -c user.name=Claude -c user.email=noreply@anthropic.com commit …`.
- Sube cambios a GitHub solo cuando el dueño lo pida. Las tareas programadas suben los datos solas (ver abajo).
- La agenda no depende de Google Calendar ni enlaza a él: no lo añadas.

## Cómo está montado
| Pieza | Dónde | Qué hace |
|---|---|---|
| Página | `pokemon-go-agenda/index.html` y `sprites2.webp` | Cinco pestañas: Agenda, Pases, Top (atacantes), Raids y Rocket. Lee la base de datos del artifact con `window.claude.use("db")` y `db.doc(ruta).onSnapshot`. **Nunca escribe en ella** (una versión antigua que escribía borró los pases de pago). |
| Base de datos del artifact | `agenda/snapshot`, `meta/atacantes`, `meta/atacantes-max`, `meta/rocket`, `meta/raids` y `meta/scripts` | Lo que pinta la página. `meta/scripts` guarda el código de los scripts que usan las tareas (campos `agenda`, `raids`, `rocket` y `actualizar_atacantes`). |
| Datos | `datos/*.json` | Copia de esos documentos (formatos en el README) más `eventos.json`, que se genera de `agenda.json`. |
| Scripts | `scripts/` | Descargan y validan. Dicen `IGUAL` o `CAMBIA` y, si una web cambia de formato, paran con `ERROR` sin tocar nada. |
| Tareas programadas | claude.ai/code/routines | «Raids de Pokémon GO (diario)», a las 9:41. «Eventos Pokémon GO al calendario», los lunes a las 0:05: eventos, copia opcional en Google Calendar, notificación al móvil, Team GO Rocket y, el primer lunes de cada mes, atacantes. Las dos van con Sonnet, tienen este repo conectado y al final suben a `main` con `scripts/subir.py`. |

Las tareas sacan los scripts de `meta/scripts`, no de este repo; solo `subir.py` y `eventos_json.py` los ejecutan desde una copia del repo. **Si cambias `agenda.py`, `raids.py`, `rocket.py` o `actualizar_atacantes.py`, actualiza también `meta/scripts`** (ArtifactData `get`, cambia el campo y `set` con `if_version`) o las tareas seguirán usando el viejo.

Las tareas se ven y se cambian con `list_triggers`, `get_trigger` y `update_trigger` (servidor claude-code-remote). Con `prompt`, `update_trigger` sustituye el texto entero: parte del actual, cambia solo lo necesario y compara el antes y el después. No lances la del lunes para probar: manda una notificación al móvil y escribe en el calendario. Las tareas no tienen `add_repo`: el repo se les conecta desde claude.ai/code/routines (Edit → Advanced settings → General → Repository).

## Cambiar la página
1. Edita `pokemon-go-agenda/index.html`. Es un fragmento sin `<html>` ni `<head>`: el artifact le pone el esqueleto al publicarla.
2. Pruébala con `node pruebas/pagina.js` (ver «Pruebas»). Tiene que terminar en `OK`.
3. Publícala con el Artifact tool encima del artifact que ya existe, titulado «Agenda Pokémon GO». Búscalo con `action: "list"` o pide el enlace al dueño, y léelo antes con `action: "read"`. Pasa `file_path` = el `index.html` y `files` = `{"sprites2.webp": "<ruta de pokemon-go-agenda/sprites2.webp>"}`; si rechaza las rutas, copia los dos archivos a tu scratchpad. Si hace falta volver a declarar los permisos: `capabilities` = `{"db":{"rules":[{"path":"","read":"view","write":"owner"},{"path":"agenda","read":"view","write":"owner"}]}}`.
4. Diseño: los colores son tokens en `:root` con su versión oscura. Hay 16 px de margen lateral, los emojis de las pestañas se ocultan por debajo de 420 px y todo tiene que caber en 320 px.

## Fotos de los Pokémon
`sprites2.webp` es una hoja de 32 columnas con celdas de 72 px (1316 iconos del juego). `SPR_IDS`, dentro de `index.html`, lista los iconos en el mismo orden (`pm<n.º>` o `pm<n.º>.f<FORMA>`). Si falta un icono, la página pinta un círculo del color del tipo; las formas nuevas usan la foto de la forma normal. Cuando salgan Pokémon nuevos, rehazla con los iconos de PokeMiners/pogo_assets (cdn.leekduck.com está bloqueado; hace falta Pillow):
```bash
git clone -q --depth 1 --filter=blob:none --sparse https://github.com/PokeMiners/pogo_assets.git /tmp/pa
git -C /tmp/pa sparse-checkout set "Images/Pokemon - 256x256/Addressable Assets"
ls "/tmp/pa/Images/Pokemon - 256x256/Addressable Assets" > /tmp/todos.txt
python3 scripts/sprites.py lista /tmp/todos.txt /tmp/sel.txt
python3 scripts/sprites.py hoja "/tmp/pa/Images/Pokemon - 256x256/Addressable Assets" /tmp/sel.txt pokemon-go-agenda/sprites2.webp /tmp/ids.txt 72 32
```
Después pega el contenido de `/tmp/ids.txt` en `SPR_IDS`, prueba y publica.

## Pruebas
- `node pruebas/pagina.js` abre la página en Chromium (Playwright) con una base de datos simulada hecha con `datos/*.json`. La prueba en claro y en oscuro a 390, 360 y 320 px, recorre las cinco pestañas y comprueba que no hay errores de JavaScript ni scroll lateral, que las pestañas caben en una línea, que cada pestaña pinta algo, qué fotos faltan y que la página no escribe en la base de datos. Deja capturas en `pruebas/capturas/` (no se suben).
- Los scripts se pueden probar sin red con HTML ya descargado: `raids.py --html CARPETA`, `rocket.py --html PAGINA.html` y `actualizar_atacantes.py --html CARPETA`.
- `subir.py` se prueba contra un repo local, sin tocar GitHub: `git clone -q --bare . /tmp/r.git && git clone -q /tmp/r.git /tmp/c` y ejecutar `/tmp/c/scripts/subir.py`.

## Red
Permitidos: leekduck.com, db.pokemongohub.net, pokemongo.com, store.pokemongo.com y GitHub por git. Bloqueado: cdn.leekduck.com.
