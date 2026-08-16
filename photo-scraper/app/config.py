"""Configuración del servicio: tiempos, UA y modo de lanzamiento del navegador."""
import os

# Tiempo máximo (ms) esperando a que Google cargue y procese la página.
TIMEOUT_MS = int(os.environ.get("PHOTO_TIMEOUT_MS", "15000"))

# Tiempo (ms) esperando a que aparezca la primera miniatura de resultados.
THUMB_WAIT_MS = int(os.environ.get("PHOTO_THUMB_WAIT_MS", "8000"))

# Headed bajo Xvfb por defecto: los UAs de Linux/headless eran bloqueados por
# Google con mucha más frecuencia. Con `PHOTO_HEADLESS=1` se fuerza headless.
HEADLESS = os.environ.get("PHOTO_HEADLESS", "0") == "1"

USER_AGENT = os.environ.get(
    "PHOTO_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
)

VIEWPORT = {"width": 1280, "height": 900}

CHROMIUM_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",
    "--lang=es-ES",
    "--window-size=1280,900",
]