"""Fixtures de test.

Els tests s'executen contra PostgreSQL (docker) usant una base de dades
dedicada (`TEST_DATABASE_NAME`) per no tocar la base de dades real.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import httpx
import psycopg2
import psycopg2.extensions
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth.dependencies import get_google_verifier
from app.auth.google import GoogleUserInfo
from app.auth.models import RoleKey, User
from app.auth.repository import AuthRepository
from app.core.config import settings
from app.core.deps import get_db

# Importa todos los modelos (incluidos los sociales) para que
# SQLModel.metadata.create_all del test DB cree también las tablas nuevas.
import app.models  # noqa: E402,F401

TEST_DATABASE_URL = settings.test_database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)


def _create_test_database() -> None:
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname="postgres",
        connect_timeout=5,
    )
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (settings.test_database_name,),
        )
        exists = cur.fetchone()
        if not exists:
            cur.execute(f'CREATE DATABASE "{settings.test_database_name}"')
    conn.close()


async def _init_schema(engine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        # Recrea el esquema cada sesión: create_all no altera taules ja
        # existents i una BD de test persistent quedaria desactualitzada
        # enfront dels models nous.
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        repo = AuthRepository(session)
        for role in RoleKey:
            if await repo.get_role_by_name(role.value) is None:
                await repo.create_role(role.value)
        await session.commit()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    _create_test_database()
    # NullPool: cada sessió obté una connexió nova al loop actual, evitant
    # el problema "attached to a different loop" amb pytest-asyncio.
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    await _init_schema(engine)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def session_factory(test_engine):
    return async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest.fixture(autouse=True)
async def _clean_tables(test_engine, session_factory) -> AsyncGenerator[None, None]:
    async with test_engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE refresh_tokens, user_roles, "
                "email_verification_tokens, password_reset_tokens, "
                "reports, activities, mutes, blocks, follows, "
                "review_likes, reviews, ratings, "
                "posts, post_media, post_likes, comments, comment_likes, mentions, "
                "lists, list_items, list_collaborators, "
                "notifications, notification_settings, push_queue, "
                "reading_progress, shelf_items, user_books, shelves, "
                "reading_goals, privacy_settings, profile_preferences, "
                "profiles, "
                "users, roles RESTART IDENTITY CASCADE"
            )
        )
    async with session_factory() as session:
        repo = AuthRepository(session)
        for role in RoleKey:
            if await repo.get_role_by_name(role.value) is None:
                await repo.create_role(role.value)
        await session.commit()
    yield


@pytest.fixture
async def db_session(session_factory) -> AsyncGenerator[AsyncSession, None]:
    async with session_factory() as session:
        yield session


class FakeGoogleVerifier:
    """Verificador de Google controlable des dels tests."""

    def __init__(self) -> None:
        self.info = GoogleUserInfo(
            sub="google-sub-123",
            email="google.user@example.com",
            name="Google User",
            email_verified=True,
        )
        self.should_fail = False

    async def verify(self, credential: str) -> GoogleUserInfo:
        if self.should_fail:
            from app.auth.exceptions import GoogleTokenInvalidError

            raise GoogleTokenInvalidError("fake invalid token")
        return self.info


@pytest.fixture
def google_verifier() -> FakeGoogleVerifier:
    return FakeGoogleVerifier()


@pytest.fixture
async def client(
    session_factory, google_verifier
) -> AsyncGenerator[httpx.AsyncClient, None]:
    from app.main import app

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    # Los handlers de contadores (reviews) escriben en la BD de test.
    from app.reviews import counters as review_counters

    review_counters.set_session_factory(session_factory)

    # Los handlers de notificaciones (F8) escriben en la BD de test.
    from app.notifications import handlers as notification_handlers

    notification_handlers.set_session_factory(session_factory)

    app.dependency_overrides[get_google_verifier] = lambda: google_verifier
    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def create_user(
    session_factory,
    *,
    email: str = "user@example.com",
    username: str = "regularuser",
    password: str = "Str0ng!Passw0rd",
    roles: list[RoleKey] | None = None,
) -> User:
    """Crea un usuari directament a la base de dades (per als tests de permisos)."""
    from app.auth.security import hash_password

    async with session_factory() as session:
        repo = AuthRepository(session)
        user = await repo.create_user(
            email=email,
            username=username,
            hashed_password=hash_password(password),
            is_email_verified=True,
        )
        if roles:
            for role in roles:
                if role.value != RoleKey.USER.value:
                    await repo.add_roles(user.id, [role])
        await session.commit()
        fresh = await repo.get_by_id(user.id)
        return fresh


def valid_password() -> str:
    return "Str0ng!Passw0rd"


def random_email(prefix: str = "user") -> str:
    return f"{prefix}.{uuid.uuid4().hex[:8]}@example.com"
