"""Configuració central de l'aplicació utilitzant pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuració de l'aplicació carregada des de variables d'entorn."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )
    
    # Base de dades PostgreSQL
    postgres_user: str
    postgres_password: str
    postgres_host: str = "db"
    postgres_port: int = 5432
    postgres_db: str
    
    # API
    api_port: int = 8000
    
    # Google Books API
    google_api_key: str | None = None
    
    @property
    def database_url(self) -> str:
        """Construeix l'URL de connexió a la base de dades."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


# Instància singleton de la configuració
settings = Settings()
