# Agenda Pokémon GO · copia de seguridad

`index.html` es el código de la agenda visual: una página publicada como artifact de Claude con cinco pestañas:

- **Agenda**: los eventos de Pokémon GO en hora de España, con bonificaciones, pases, incursiones y su valoración.
- **Pases**: lo que da cada opción de pago frente a lo gratis, con precios en euros.
- **Top**: los mejores atacantes de incursiones y de Combates Max, con la foto de cada Pokémon.
- **Raids**: los jefes de ahora y los próximos, a qué tipos son débiles y sus mejores counters con foto.
- **Rocket**: buscas la frase del recluta o del líder y ves su equipo y el Pokémon oscuro que puedes capturar.

La página no depende de Google Calendar: todo lo lee de su propia base de datos, que actualizan las tareas programadas.

## Cómo restaurarla

1. Pídele a Claude que publique `index.html` como artifact con `sprites2.webp` al lado (la imagen con los iconos de los Pokémon) y con la capacidad **Base de datos** (`db`) con estas reglas: lectura para quien vea la página y escritura solo para el dueño, en la raíz y en `agenda`.
2. Carga en la base de datos de la agenda estos documentos:

| Documento | Archivo |
|---|---|
| `agenda/snapshot` | `datos/agenda.json` |
| `meta/atacantes` | `datos/atacantes-incursiones.json` |
| `meta/atacantes-max` | `datos/atacantes-max.json` |
| `meta/rocket` | `datos/rocket.json` |
| `meta/raids` | `datos/raids.json` |
| `meta/scripts` | un JSON con el código de los scripts: `{"agenda": …, "raids": …, "rocket": …, "actualizar_atacantes": …}` (de la carpeta `scripts/`) |

Las tareas programadas sacan los scripts de `meta/scripts`, los ejecutan y guardan el resultado en el documento que toca.
