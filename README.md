# PokemonGoAPI

Datos de Pokémon GO en JSON (eventos, mejores atacantes, raids actuales con sus counters y equipos del Team GO Rocket), los scripts que los actualizan y una copia de seguridad de mi agenda visual. Las horas son de España peninsular (Europe/Madrid) y los precios, en euros de la tienda web de España.

## Qué hay

| Archivo | Qué tiene |
|---|---|
| `datos/agenda.json` | La lista de eventos tal como la guarda la agenda (documento `agenda/snapshot`): título, inicio, fin y descripción de cada evento «Pokémon GO:». |
| `datos/eventos.json` | Los mismos eventos ya separados: tipo, inicio y fin, bonificaciones gratis, pases gratis, GO Pass gratis, incursiones y Combates Max, opciones de pago con lo que dan y su valoración, texto y enlace a la noticia. |
| `datos/raids.json` | Las raids de ahora y las de los próximos días (rotaciones con sus fechas): cada jefe con su icono, tipos, PC normal y con clima, climas que lo potencian, si puede salir variocolor, a qué tipos es débil (×1,6 / ×2,56) y sus 12 mejores counters con ataques, eDPS y categoría. |
| `datos/atacantes-incursiones.json` | Los 10 mejores atacantes de incursiones de cada tipo, con su icono, sus ataques (MT élite y Plus marcados), eDPS y % del n.º 1, más las opciones destacadas: alternativa no legendaria, mejor sin MT élite, mejor oscuro y mejor Mega. |
| `datos/atacantes-max.json` | Los mejores atacantes de Combates Max de cada tipo, con su icono e indicando si son **Gigamax**, **Dinamax** o **Especial**, con su ataque rápido, su ataque Max y el daño. Incluye el mejor sin Gigamax y el mejor sin MT élite. |
| `datos/rocket.json` | Los equipos actuales de los reclutas, los líderes y Giovanni: la frase del juego en español, los 3 puestos de su equipo con el icono, tipos y debilidades de cada Pokémon, y cuáles se pueden capturar. |
| `scripts/agenda.py` | Añade, sustituye o quita eventos de `datos/agenda.json` sin duplicar, comprueba el formato (precios en euros, horas, etiquetas) y quita los que ya han terminado. |
| `scripts/eventos_json.py` | Convierte `datos/agenda.json` en `datos/eventos.json`. |
| `scripts/raids.py` | Descarga las rotaciones de raids de Leek Duck y los counters de cada jefe de Pokémon GO Hub y genera `datos/raids.json`. Los textos de Leek Duck (en inglés) se traducen una vez con `raids.py traducir` y se reutilizan. |
| `scripts/actualizar_atacantes.py` | Descarga las dos clasificaciones de Pokémon GO Hub y vuelve a generar los dos JSON de atacantes. |
| `scripts/rocket.py` | Descarga los equipos del Team GO Rocket de Leek Duck y genera `datos/rocket.json` con las frases oficiales en español. |
| `scripts/subir.py` | Lo usan las tareas programadas: copia a `datos/` los JSON que han cambiado, vuelve a generar `eventos.json` y lo sube a GitHub. |
| `scripts/sprites.py` | Monta la imagen con los iconos de los Pokémon (`pokemon-go-agenda/sprites2.webp`) a partir de los iconos del juego. |
| `pruebas/pagina.js` | Prueba la agenda en un navegador con los datos de `datos/`: modo claro y oscuro, anchos de móvil y las cinco pestañas (`node pruebas/pagina.js`). |
| `CLAUDE.md` | Guía para Claude: cómo está montado todo y cómo cambiarlo sin romper nada. |
| `pokemon-go-agenda/` | Copia de seguridad de la agenda visual: su código, la imagen de iconos y cómo restaurarla. |

Todos los scripts solo reescriben su JSON si la fuente se ha leído bien y dicen si ha cambiado algo (`IGUAL` / `CAMBIA`); si una web cambia de formato, paran con `ERROR` y no tocan nada.

## Cómo se actualiza

```bash
python3 scripts/raids.py                   # raids de ahora y próximas con sus counters (menos de 1 min)
python3 scripts/rocket.py                  # equipos del Team GO Rocket
python3 scripts/actualizar_atacantes.py    # mejores atacantes de incursiones y de Combates Max (unos 20 s)
python3 scripts/agenda.py ver              # eventos guardados; «poner», «quitar» y «guardar» para cambiarlos
python3 scripts/eventos_json.py datos/agenda.json
```

Solo hace falta Python 3 y `curl`; `sprites.py` usa además Pillow. En la agenda lo hacen solas dos tareas programadas de Claude, que al terminar suben aquí los JSON que hayan cambiado (con `scripts/subir.py`):

- **Cada día a las 9:41**: las raids.
- **Cada lunes a las 0:00**: los eventos nuevos (y su copia en Google Calendar si está disponible) y los equipos del Team GO Rocket; el primer lunes de cada mes, también los mejores atacantes.

## Fuentes

- Eventos: noticias oficiales de [pokemongo.com](https://pokemongo.com/news) y [Leek Duck](https://leekduck.com/events/).
- Raids: jefes, PC y fechas de [Leek Duck](https://leekduck.com/raid-bosses/); counters de [Pokémon GO Hub](https://db.pokemongohub.net/) (simulados contra cada jefe, nivel 50, IV 15/15/15, sin clima ni amistad); debilidades según la tabla de tipos del juego.
- Atacantes: [Pokémon GO Hub](https://db.pokemongohub.net/es/pokemon-list/best-per-type) (mejores atacantes por tipo y mejores atacantes Dinamax por tipo). En incursiones se ordena por eDPS; en Combates Max, por el daño de un ataque Max de nivel 3.
- Team GO Rocket: equipos de [Leek Duck](https://leekduck.com/rocket-lineups/); frases, nombres de objetos y ataques en español de los textos del juego ([PokeMiners/pogo_assets](https://github.com/PokeMiners/pogo_assets)).
- Iconos de los Pokémon: los del juego, de [PokeMiners/pogo_assets](https://github.com/PokeMiners/pogo_assets).

Proyecto personal, sin relación con Scopely, Niantic, Nintendo, The Pokémon Company, Leek Duck ni Pokémon GO Hub.
