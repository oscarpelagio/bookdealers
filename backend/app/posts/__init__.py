"""Posts & Engagement (FASE 6).

Posts, media, comentarios (anidado 1 nivel), likes y menciones.
Las publicaciones generan actividad (verbos POST/COMMENTED) que el feed
(F5) ya consume; las menciones emiten el evento `posts.mention_detected`
que alimentará las notificaciones (F8).
"""
