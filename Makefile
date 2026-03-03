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