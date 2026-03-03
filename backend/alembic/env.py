"""Configuració d'Alembic per a migracions de base de dades."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

from alembic import context

# Importa els models perquè Alembic els detecti
from app.core.config import settings
from app.models import Book

# Aquest és l'objecte Config d'Alembic
config = context.config

# Configura el logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadades per a l'autogeneració de migracions
target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Executa migracions en mode 'offline'."""
    url = settings.database_url
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Executa migracions en mode 'online'."""
    # Configura amb la URL de la base de dades
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = settings.database_url
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,  # Compara tipus de columnes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
