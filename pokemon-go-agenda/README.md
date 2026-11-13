# Agenda Pokémon GO · copia de seguridad

`index.html` es el código de la agenda visual: una página publicada como artifact de Claude que enseña los eventos de Pokémon GO del Google Calendar (hora de Barcelona), los pases de pago y los mejores atacantes de incursiones y de Combates Max.

## Cómo restaurarla

Pídele a Claude que publique `index.html` como artifact con estas capacidades:

- **Google Calendar** (`list_events`): la página lee los eventos que empiezan por «Pokémon GO:».
- **Base de datos**: lectura para quien vea la página y escritura solo para el dueño.
- **Usuario** (`user`): para saber si quien la abre es el dueño.

Después, carga en la base de datos de la agenda (colección `meta`):

| Documento | Archivo |
|---|---|
| `atacantes` | `datos/atacantes-incursiones.json` |
| `atacantes-max` | `datos/atacantes-max.json` |

La copia de los eventos para invitados (`agenda/snapshot`) se crea sola la primera vez que el dueño abre la página.
