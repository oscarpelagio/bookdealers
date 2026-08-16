"""Recomendaciones (FASE 11).

Read-models derivados (ADR-6, sin tablas):
- `GET /recommendations`: colaborativo por autor (F3 ratings) con fallback
  a populares en datos fríos (sin historial).
- `GET /feed/popular`: posts populares por engagement
  (likes*2 + comentarios*3), con visibilidad.
"""