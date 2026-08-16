FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN apt-get update && apt-get install -y \
    xvfb \
    xauth \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium

COPY . .

EXPOSE 8002

# Chromium headed bajo Xvfb (más resistente al anti-bot de Google que el modo
# headless). Se arranca Xvfb en un display fijo y uvicorn como PID1 con
# DISPLAY exportado.
CMD ["sh", "-c", "rm -f /tmp/.X99-lock /tmp/.X11-unix/X99 && Xvfb :99 -screen 0 1280x900x24 -nolisten tcp >/tmp/xvfb.log 2>&1 & sleep 1 && export DISPLAY=:99 && exec uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload"]