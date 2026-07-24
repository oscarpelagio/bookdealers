# Z39.50 Proxy — BookTracker

FastAPI microservice that acts as a proxy to the Z39.50 protocol to check book availability in Catalan library catalogs (ALADI, Argus) using `yaz-client`.

## What is Z39.50

Z39.50 is a standard protocol (ISO 23950) for search and retrieval in bibliographic databases. Catalan libraries (Barcelona Provincial Council, Generalitat) expose their catalogs via this protocol.

This service encapsulates Z39.50 complexity behind a simple HTTP endpoint that the backend can consume.

## Architecture

```
app/
├── main.py               # FastAPI app + health check
├── config.py             # Z39.50 catalog hosts and ports
├── clients/
│   └── client.py         # Async wrapper around yaz-client (subprocess)
├── services/
│   └── service.py        # Service layer (delegates to the client)
└── routers/
    ├── router.py          # Main router (prefix /Z3950-search)
    ├── dependencies.py    # DI: Client → Service
    └── endpoints/
        └── router.py      # GET /search
```

## Query flow

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

## Z39.50 protocol — commands

The client sends these commands to `yaz-client` via stdin:

```
base INNOPAC                          # Select database
find @and                             # AND operator
  @attr 1=4 @attr 3=3 @attr 4=6      # Title search (attr 1=4)
    "don quixote"                     #   exact match
  @attr 1=1003 @attr 3=3 @attr 4=6   # AND author (attr 1=1003)
    "cervantes"                       #   exact match
format opac                           # OPAC format (includes holdings)
show 1+50                             # Show records 1 to 50
exit                                  # Close connection
```

Z39.50 attributes used:
| Attr | Value | Meaning |
|------|-------|---------|
| 1 (Use) | 4 | Title |
| 1 (Use) | 1003 | Author |
| 3 (Structure) | 3 | Key |
| 4 (Truncation) | 6 | Truncation: complete field |

## Configured catalogs

Defined in `config.py`:

| Catalog | Host | Port | Base | Coverage |
|---------|------|------|------|----------|
| **ALADI** | `aladi.diba.cat` | 210 | INNOPAC | Barcelona Provincial Council libraries |
| **Argus** | `elmeuargus.biblioteques.gencat.cat` | 210 | INNOPAC | Generalitat of Catalonia libraries |

Currently only ALADI is used. The config includes both for future expansion.

## Endpoint

### `GET /search`

| Param | Type | Description |
|-------|------|-------------|
| `title` | string | Normalized book title |
| `author` | string | Normalized book author |

**Response:**
```json
{
  "response": "Record type: USmarc\n907  $f spa\n...\nData holdings\nlocalLocation: BCN.Biblioteca Jaume Fuster\npublicNote: Available\n..."
}
```

The raw MARC text is parsed by `Z3950Adapter` in the backend, not here. This service only acts as a proxy.

## MARC response format (OPAC)

The response contains MARC records separated by `Record type: USmarc`, each with:

```
Record type: USmarc
...
907  $f spa                              ← Language (field 907 subfield $f)
...
Data holdings                            ← Start of a copy
  localLocation: BCN.Jaume Fuster        ← Library
  publicNote: Available                  ← Status (Available, DUE 20-03-26, In Transit...)
Data holdings                            ← Next copy
  localLocation: TERRASSA.Central
  publicNote: DUE 15-04-26
```

A book can have multiple editions (MARC records), and each edition multiple copies (holdings).

## Dependencies

| Package | Use |
|---------|-----|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `yaz` | Z39.50 client (apt package, no pip) |

## Docker

```dockerfile
FROM python:3.11-slim
RUN apt-get install -y yaz    # Install yaz-client
```

`yaz-client` is a C tool from the YAZ project. It is installed via `apt`, not pip. That is why this service needs its own container — it isolates the system dependency.

## Development

```bash
# Start only this service
docker compose up z3950 -d --build

# Health check
curl http://localhost:8001/health

# Direct test
curl "http://localhost:8001/search?title=house+spirits&author=allende"
```
