"""Búsqueda social (FASE 10).

`search_users` / `search_books` / `search_posts` como queries sobre las
tablas existentes (users/profiles, books, posts) con normalización de
tildes (NormalizationUtils) y filtrado de visibilidad. Sin tablas nuevas;
la migración solo añade índices pg_trgm (perf).
"""