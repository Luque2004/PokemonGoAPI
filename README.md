# PokemonGoAPI

Datos de Pokémon GO en JSON (eventos y mejores atacantes), los scripts que los actualizan y una copia de seguridad de mi agenda visual. Las horas son de España peninsular (Europe/Madrid).

## Qué hay

| Archivo | Qué tiene |
|---|---|
| `datos/eventos.json` | Los eventos de la agenda: tipo, inicio y fin, bonificaciones gratis, pases gratis, GO Pass gratis, incursiones y Combates Max, opciones de pago con lo que dan y su valoración, texto y enlace a la noticia. |
| `datos/atacantes-incursiones.json` | Los 10 mejores atacantes de incursiones de cada tipo, con sus ataques (MT élite y Plus marcados), eDPS y % del n.º 1, más las opciones destacadas: alternativa no legendaria, mejor sin MT élite, mejor oscuro y mejor Mega. |
| `datos/atacantes-max.json` | Los mejores atacantes de Combates Max de cada tipo, indicando si son **Gigamax**, **Dinamax** o **Especial** (formas con un ataque Max propio, como Zacian y Zamazenta coronados o Eternatus), con su ataque rápido, su ataque Max y el daño. Incluye el mejor sin Gigamax y el mejor sin MT élite. |
| `scripts/actualizar_atacantes.py` | Descarga las dos clasificaciones de Pokémon GO Hub y vuelve a generar los dos JSON de atacantes. Solo los reescribe si la fuente ha cambiado (`IGUAL` / `CAMBIA`) y no toca nada si la página no se lee bien. |
| `scripts/eventos_json.py` | Convierte la copia de la agenda (los eventos «Pokémon GO:» del calendario) en `datos/eventos.json`. |
| `pokemon-go-agenda/` | Copia de seguridad de la agenda visual: su código y cómo restaurarla. |

## Cómo se actualiza

```bash
python3 scripts/actualizar_atacantes.py          # descarga y actualiza los atacantes (tarda unos 20 s)
python3 scripts/eventos_json.py copia.json       # copia.json = documento agenda/snapshot de la agenda
```

Solo hace falta Python 3 y `curl`. Los scripts no usan librerías externas.

## Fuentes

- Eventos: noticias oficiales de [pokemongo.com](https://pokemongo.com/news) y [Leek Duck](https://leekduck.com/events/).
- Atacantes: [Pokémon GO Hub](https://db.pokemongohub.net/es/pokemon-list/best-per-type) (mejores atacantes por tipo y mejores atacantes Dinamax por tipo). Nivel 40, IV 15/15/15, sin clima. En incursiones se ordena por eDPS; en Combates Max, por el daño de un ataque Max de nivel 3.

Proyecto personal, sin relación con Scopely, Nintendo, The Pokémon Company ni Pokémon GO Hub.
