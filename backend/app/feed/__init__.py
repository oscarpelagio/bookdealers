"""Feed v1 (read-model) — FASE 5.

Sin migraciones de negocio: el feed es una consulta sobre `activities`
(F4). Timeline propia = actividades de los usuarios a los que sigo + las
mías, filtradas por visibilidad (cada actividad guarda su snapshot ADR-4),
bloqueo (los blocks borran follows, así que quedan excluidos por
construcción) y mute (excluyo a los silenciados del pool de actores).
"""

from __future__ import annotations
