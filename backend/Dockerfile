FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY requirements-dev.txt .

RUN pip install --no-cache-dir -r requirements-dev.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# We use the absolute path to avoid PATH errors
ENTRYPOINT ["/app/entrypoint.sh"]
