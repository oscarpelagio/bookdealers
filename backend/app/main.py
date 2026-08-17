"""Main application"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.auth.exceptions import AuthError
from app.auth.service import seed_default_roles
from app.core.author_seed import seed_author_data
from app.core.catalog_seed import seed_catalogs
from app.core.seed_aladi import seed_aladi
from app.core.exceptions import DomainError
from app.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # El esquema lo gestiona Alembic (ver entrypoint.sh: `alembic upgrade head`).
    # Se evita `create_all` para no chocar con las migraciones en dev (--reload).
    await seed_catalogs()
    await seed_aladi()
    await seed_author_data()
    await seed_default_roles()
    yield


app = FastAPI(title="Book Tracker API", lifespan=lifespan, swagger_ui_parameters={"displayRequestDuration": True})


@app.exception_handler(AuthError)
async def auth_error_handler(request: Request, exc: AuthError) -> JSONResponse:
    headers = {"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None
    return JSONResponse(status_code=exc.status_code, content=exc.to_payload(), headers=headers)


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.to_payload())


app.include_router(api_router)


@app.get("/", tags=["Backend"])
def status():
    return {"status": "ok", "message": "Running"}
