# Z39.50 Proxy — BookTracker

Microservicio FastAPI que actúa como proxy al protocolo Z39.50 para consultar disponibilidad de libros en catálogos bibliotecarios catalanes (ALADI, Argus) usando `yaz-client`.

## Qué es Z39.50

Z39.50 es un protocolo estándar (ISO 23950) para búsqueda y recuperación de información en bases de datos bibliográficas. Las bibliotecas catalanas (Diputació de Barcelona, Generalitat) exponen sus catálogos via este protocolo.

Este servicio encapsula la complejidad de Z39.50 en un endpoint HTTP simple que el backend puede consumir.

## Arquitectura

```
app/
├── main.py               # FastAPI app + health check
├── config.py             # Hosts y puertos de catálogos Z39.50
├── clients/
│   └── client.py         # Wrapper async sobre yaz-client (subprocess)
├── services/
│   └── service.py        # Capa de servicio (delega al client)
└── routers/
    ├── router.py          # Router principal (prefix /Z3950-search)
    ├── dependencies.py    # DI: Client → Service
    └── endpoints/
        └── router.py      # GET /search
```

## Flujo de una consulta

```
Backend                    Z3950 Service              yaz-client            ALADI
  │                            │                          │                   │
  │  GET /search               │                          │                   │
  │  ?title=X&author=Y         │                          │                   │
  ├───────────────────────────►│                          │                   │
  │                            │                          │                   │
  │                            │  spawn subprocess        │                   │
  │                            ├─────────────────────────►│                   │
  │                            │                          │                   │
  │                            │  stdin commands:         │                   │
  │                            │  base INNOPAC            │                   │
  │                            │  find @and @attr...      │  Z39.50 query     │
  │                            │  format opac             ├──────────────────►│
  │                            │  show 1+50               │  ◄── MARC data  ──┤
  │                            │  exit                    │                   │
  │                            │                          │                   │
  │                            │  ◄── stdout (MARC text) ─┤                   │
  │                            │                          │                   │
  │  ◄── {"response": "..."} ──┤                          │                   │
```

## Protocolo Z39.50 — Commands

El client envía estos comandos a `yaz-client` via stdin:

```
base INNOPAC                          # Seleccionar base de datos
find @and                             # Operador AND
  @attr 1=4 @attr 3=3 @attr 4=6      # Búsqueda por título (attr 1=4)
    "don quijote"                     #   con coincidencia exacta
  @attr 1=1003 @attr 3=3 @attr 4=6   # AND por autor (attr 1=1003)
    "cervantes"                       #   con coincidencia exacta
format opac                           # Formato OPAC (incluye holdings)
show 1+50                             # Mostrar registros 1 a 50
exit                                  # Cerrar conexión
```

Atributos Z39.50 usados:
| Attr | Valor | Significado |
|------|-------|-------------|
| 1 (Use) | 4 | Title |
| 1 (Use) | 1003 | Author |
| 3 (Structure) | 3 | Key |
| 4 (Truncation) | 6 | Truncation: complete field |

## Catálogos configurados

Definidos en `config.py`:

| Catálogo | Host | Puerto | Base | Cobertura |
|----------|------|--------|------|-----------|
| **ALADI** | `aladi.diba.cat` | 210 | INNOPAC | Biblioteques de la Diputació de Barcelona |
| **Argus** | `elmeuargus.biblioteques.gencat.cat` | 210 | INNOPAC | Biblioteques de la Generalitat de Catalunya |

Actualmente solo se usa ALADI. El config tiene ambos preparados para expansión futura.

## Endpoint

### `GET /search`

| Param | Tipo | Descripción |
|-------|------|-------------|
| `title` | string | Título normalizado del libro |
| `author` | string | Autor normalizado del libro |

**Response:**
```json
{
  "response": "Record type: USmarc\n907  $f spa\n...\nData holdings\nlocalLocation: BCN.Biblioteca Jaume Fuster\npublicNote: Available\n..."
}
```

El texto raw MARC es parseado por `Z3950Adapter` en el backend, no aquí. Este servicio solo actúa como proxy.

## Formato de respuesta MARC (OPAC)

La respuesta contiene registros MARC separados por `Record type: USmarc`, cada uno con:

```
Record type: USmarc
...
907  $f spa                              ← Idioma (campo 907 subcampo $f)
...
Data holdings                            ← Inicio de una copia
  localLocation: BCN.Jaume Fuster        ← Biblioteca
  publicNote: Available                  ← Estado (Available, DUE 20-03-26, In Transit...)
Data holdings                            ← Siguiente copia
  localLocation: TERRASSA.Central
  publicNote: DUE 15-04-26
```

Un libro puede tener múltiples ediciones (registros MARC) y cada edición múltiples copias (holdings).

## Dependencias

| Paquete | Uso |
|---------|-----|
| `fastapi` | Framework web |
| `uvicorn` | ASGI server |
| `yaz` | Cliente Z39.50 (apt package, no pip) |

## Docker

```dockerfile
FROM python:3.11-slim
RUN apt-get install -y yaz    # Instala yaz-client
```

`yaz-client` es una herramienta C del proyecto YAZ. Se instala via `apt`, no pip. Por eso este servicio necesita su propio contenedor — aisla la dependencia del sistema.

## Desarrollo

```bash
# Levantar solo este servicio
docker compose up z3950 -d --build

# Health check
curl http://localhost:8001/health

# Test directo
curl "http://localhost:8001/search?title=casa+espiritus&author=allende"
```
