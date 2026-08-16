# ---- Env File: ----
env:
	cp .env.example .env


# ---- Docker: ----
build:
	docker compose up -d --build
up:
	docker compose up -d
down:
	docker compose down


# ---- Frontend: ----
front-up:
	docker compose up -d front
front-logs:
	docker compose logs -f front
front-install:
	docker compose exec front npm install


# ---- Alembic Migrations: ----
new-migration:
	docker exec -i back alembic revision --autogenerate -m "$(m)"
migrate:
	docker exec -i back alembic upgrade head
migration-downgrade:
	docker exec -i back alembic downgrade -1
migration-history:
	docker exec -i back alembic history --verbose
current-migration:
	docker exec -i back alembic current


# ---- Tests: ----
# Requiere la base de datos docker levantada (make up).
test:
	docker compose exec back pytest -q


# ---- iPhone (dev build nativa, ver frontend/DEV-IPHONE.md) ----
DEVICE := Oscar
FRONTEND_DIR := frontend

# Preflight: valida docker, backend, IP LAN y dispositivo antes de compilar.
iphone-preflight:
	@if ! docker compose ps >/dev/null 2>&1; then \
		echo "ERROR: el daemon de docker no está corriendo (arranca Docker/OrbStack)."; \
		exit 1; \
	fi
	@if ! curl -s -o /dev/null http://localhost:8000/; then \
		echo "ERROR: backend no responde en :8000 (haz 'make up')."; \
		exit 1; \
	fi
	@LAN_IP=$$(ipconfig getifaddr en0 2>/dev/null); \
	API_URL=$$(grep -o 'http://[0-9.]*:8000' $(FRONTEND_DIR)/.env | head -1); \
	if [ -n "$$LAN_IP" ] && [ "$${API_URL#http://}" != "$${LAN_IP}:8000" ]; then \
		echo "ERROR: EXPO_PUBLIC_API_URL=$$API_URL no coincide con la IP LAN $$LAN_IP."; \
		echo "  Actualiza $(FRONTEND_DIR)/.env y reinicia Metro con --clear."; \
		exit 1; \
	fi
	@if ! xcrun devicectl list devices | grep -q "$(DEVICE)"; then \
		echo "ERROR: iPhone '$(DEVICE)' no disponible (cable + desbloqueado + Trust)."; \
		echo "  Prueba: xcrun devicectl list devices"; \
		exit 1; \
	fi
	@echo "OK: preflight superado (docker, backend :8000, IP LAN, iPhone $(DEVICE))."

# Compilar + instalar + arrancar Metro en el iPhone físico.
iphone-run: iphone-preflight
	cd $(FRONTEND_DIR) && npx expo run:ios --device "$(DEVICE)"
