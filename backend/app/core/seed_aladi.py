"""Seed de la taula `seed_aladi` a partir d'`assets/biblioteques_diba.json` i
lògica d'enllaç amb les biblioteques (`establishments` tipus library).

S'executa a l'arrencada de l'app (lifespan) i fa un upsert per `punt_id`:
crea les biblioteques noves i actualitza les que ja existeixen amb els
últims valors del volcat. Es preserva l'element complet al camp JSONB `dades`
per poder recuperar tots els camps originals.

Quan s'afegeix una biblioteca nova a la BD (establiment tipus library), es fa
una cerca fuzzy del seu nom contra `nom` + `municipi` de la taula seed_aladi;
la fila amb més puntuació relliga el seu `id_establishment`. L'enllaç també es
replica a l'arrencada per a les biblioteques que encara no en tenen."""

import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import async_engine
from app.models import SeedAladi, Establishment

# Llindar mínim de similitud per assignar id_establishment (evita enllaços
# entre noms completament diferents).
_MIN_SCORE = 0.30


def _resolve_json_path() -> Path | None:
    candidates = [
        # Ruta dins del contenidor docker (compose munta ./assets:/app/assets).
        Path("/app/assets/biblioteques_diba.json"),
        # Ruta des d'una execució local al repo.
        Path(__file__).resolve().parents[2] / "assets" / "biblioteques_diba.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _parse_geo(localitzacio: str) -> tuple[float | None, float | None]:
    if not localitzacio:
        return None, None
    try:
        lat_s, lon_s = localitzacio.split(",")
        return float(lat_s.strip()), float(lon_s.strip())
    except (ValueError, AttributeError):
        return None, None


def _norm(text: str | None) -> str:
    """Normalitza per comparar: minúscules, sense accents, sense puntuació
    (els separadors com `.` o `-` es converteixen en espais) i espai col·lapsat."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def _extract_postal(adreca: str | None, source: str | None) -> str | None:
    """Codi postal: si el camp propi del volcat ve buit, l'extrau de les últimes
    xifres de l'adreça (els CP espanyols en són 5)."""
    if source:
        return source
    if adreca:
        match = re.findall(r"\b\d{5}\b", adreca)
        return match[-1] if match else None
    return None


def _street_seed(adreca: str | None, codi_postal: str | None, municipi: str | None) -> str | None:
    """Neteja la línia d'adreça del volcat per deixar només el carrer:
    treu el codi postal i el nom de municipi que de vegades venen incrustats
    al final (fins i tot si el camp codi_postal està buit)."""
    if not adreca:
        return None
    cleaned = adreca
    if codi_postal:
        cleaned = re.sub(re.escape(codi_postal), " ", cleaned)
    if municipi and municipi != "Barcelona":
        cleaned = re.sub(re.escape(municipi) + r"\s*$", "", cleaned)
    # Elimina repetidament els suffixes sobrants del final: "Barcelona",
    # "Barcelona - Eixample" i codis postals (podrien venir en qualsevol ordre).
    for _ in range(5):
        cleaned = re.sub(
            r"(?:\b\d{4,5}\b|Barcelona\s+-\s+\S+|Barcelona)\s*$",
            "",
            cleaned,
        )
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" ,") or None


def _best_match(query: str, rows: list[SeedAladi]) -> tuple[SeedAladi | None, float]:
    """Retorna la fila seed_aladi amb millor similitud contra nom (+ municipi).

    Compara normalitzat i amb els tokens ordenats (indiferent a l'ordre de les
    paraules). Es penalitza quan no comparteix cap token significatiu del nom
    de l'establiment, evitant enllaços falsos per la paraula genèrica
    "biblioteca" cap a una altra ciutat.
    """
    q_tokens = _norm(query).split()
    if not q_tokens:
        return None, 0.0
    q_sorted = " ".join(sorted(q_tokens))

    best: SeedAladi | None = None
    best_score = 0.0
    for row in rows:
        haystacks = [
            f"{row.nom or ''} {row.municipi or ''}",
            row.nom or "",
        ]
        best_row = 0.0
        for hay in haystacks:
            h_tokens = _norm(hay).split()
            if not h_tokens:
                continue
            overlap = len(set(q_tokens) & set(h_tokens)) / len(q_tokens)
            if overlap <= 0.0:
                continue
            ratio = SequenceMatcher(
                None, q_sorted, " ".join(sorted(h_tokens))
            ).ratio()
            # El solapament pesa poc (0.75..1.0): el gruix de la puntuació és la
            # similitud real, per no perdre matches legítims amb codis curts.
            best_row = max(best_row, ratio * (0.75 + 0.25 * overlap))
        if best_row > best_score:
            best_score = best_row
            best = row
    return best, best_score


async def seed_aladi() -> None:
    """Volca assets/biblioteques_diba.json a la taula seed_aladi (upsert)
    i enllaça les biblioteques que encara no tenen id_establishment."""
    path = _resolve_json_path()
    if path is None:
        print("[seed_aladi] No es troba biblioteques_diba.json; seed omès.")
        return

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    elements = data.get("elements", [])
    if not elements:
        print("[seed_aladi] El volcat no conté elements; seed omès.")
        return

    print(f"[seed_aladi] Carregant {len(elements)} biblioteques des de {path}")

    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        existing_rows = {
            row.punt_id: row
            for row in (await session.exec(select(SeedAladi))).all()
        }

        created = 0
        updated = 0
        for idx, el in enumerate(elements):
            grup_adreca = el.get("grup_adreca") or {}
            rel_municipis = el.get("rel_municipis") or {}
            lat, lon = _parse_geo(el.get("localitzacio"))
            punt_id = el.get("punt_id") or f"unknown-{idx}"
            adreca = grup_adreca.get("adreca") or grup_adreca.get("adreca_completa")
            codi_postal = _extract_postal(adreca, grup_adreca.get("codi_postal") or None)

            row = existing_rows.get(punt_id)
            if row is None:
                session.add(
                    SeedAladi(
                        punt_id=punt_id,
                        nom=el.get("adreca_nom"),
                        municipi=(
                            grup_adreca.get("municipi_nom")
                            or rel_municipis.get("municipi_nom")
                        ),
                        adreca=adreca,
                        codi_postal=codi_postal,
                        lat=lat,
                        lon=lon,
                        dades=el,
                    )
                )
                created += 1
            else:
                row.nom = el.get("adreca_nom")
                row.municipi = (
                    grup_adreca.get("municipi_nom")
                    or rel_municipis.get("municipi_nom")
                )
                row.adreca = adreca
                row.codi_postal = codi_postal
                row.lat = lat
                row.lon = lon
                row.dades = el
                updated += 1

        await session.commit()

    print(f"[seed_aladi] Fet: {created} nous, {updated} actualitzats.")

    # Reenllaç: recalcula tots els id_establishment (per corregir possibles
    # matxs dolents de versions anteriors) i enllaça cada biblioteca.
    async with AsyncSession(async_engine, expire_on_commit=False) as session:
        for seed_row in (await session.exec(select(SeedAladi))).all():
            if seed_row.id_establishment is not None:
                seed_row.id_establishment = None
        await session.commit()

        libraries = (
            await session.exec(select(Establishment).where(Establishment.type == "library"))
        ).all()
        linked = 0
        for est in libraries:
            if await link_library_to_seed(session, est, force=True):
                linked += 1
        if linked:
            print(f"[seed_aladi] Enllaçades {linked} biblioteques (id_establishment).")


async def link_library_to_seed(
    session: AsyncSession, establishment: Establishment, force: bool = False
) -> bool:
    """Enllaça una biblioteca (tipus library) amb la fila seed_aladi més semblant.

    Assigna `seed_aladi.id_establishment` i fa commit. Retorna True si ha fet
    l'enllaç (o si ja existeix), False si no s'ha pogut determinar un match."""

    if establishment.type != "library":
        return False

    if not force:
        already = (
            await session.exec(
                select(SeedAladi).where(SeedAladi.id_establishment == establishment.id)
            )
        ).first()
        if already:
            return True

    seed_rows = (await session.exec(select(SeedAladi))).all()
    if not seed_rows:
        return False

    best, score = _best_match(establishment.name or "", seed_rows)
    if best is None or score < _MIN_SCORE:
        print(
            f"[aladi-link] '{establishment.name}' sense match prou bo (best={score:.2f})"
        )
        return False

    best.id_establishment = establishment.id
    await session.commit()
    print(
        f"[aladi-link] '{establishment.name}' -> '{best.nom}' ({best.municipi}) "
        f"score={score:.2f}"
    )
    return True