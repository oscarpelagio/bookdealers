"""Configuració central de l'aplicació utilitzant pydantic-settings."""

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuració de l'aplicació carregada des de variables d'entorn."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Entorn d'execució: development | production
    env: str = "development"
    debug: bool = True
    
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
    
    # Z3959
    z3950_service_url: str

    # Tiempos de expiración en segundos
    TTL_1_DAY: int = 60 * 60 * 24
    TTL_7_DAYS: int = 60 * 60 * 24 * 7

    # Scheduler (días y hora de ejecución)
    EBIBLIO_SYNC_DAYS: int = 7
    TODOSTUSLIBROS_SYNC_DAYS: int = 7
    LIBRARY_SYNC_DAYS: int = 1
    SYNC_EXECUTION_HOUR: int = 2

    # ---------- Auth / JWT ----------
    jwt_secret: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "bookdealers"
    jwt_audience: str = "bookdealers-api"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    # Clau (pepper) usada per fer HMAC dels refresh tokens abans d'emmagatzemar-los.
    token_hash_secret: SecretStr

    @field_validator("jwt_secret")
    @classmethod
    def _jwt_secret_min_length(cls, value: SecretStr) -> SecretStr:
        # HS256 requereix una clau de com a mínim 256 bits (32 bytes) reals.
        if len(value.get_secret_value().encode("utf-8")) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 bytes. Generate with: "
                "openssl rand -base64 32"
            )
        return value

    # Paràmetres Argon2id
    argon2_time_cost: int = 3
    argon2_memory_cost: int = 65536  # 64 MiB
    argon2_parallelism: int = 1

    # Política de contrasenyes
    password_min_length: int = 12
    password_max_length: int = 128
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_symbol: bool = True

    # ---------- Google OAuth ----------
    google_client_id: str | None = None
    google_jwks_url: str = "https://www.googleapis.com/oauth2/v3/certs"
    google_issuers: list[str] = [
        "accounts.google.com",
        "https://accounts.google.com",
    ]
    # Només s'accepten comptes de Google amb correu verificat per ells.
    google_require_email_verified: bool = True

    # ---------- Força bruta ----------
    login_max_attempts: int = 5
    login_lockout_seconds: int = 900  # 15 minuts, mai permanent
    rate_limit_max_requests: int = 10
    rate_limit_window_seconds: int = 60

    @field_validator("login_lockout_seconds")
    @classmethod
    def _clamp_lockout(cls, value: int) -> int:
        return max(60, min(value, 60 * 60 * 24))  # mai permanent ni acceptar 0

    # ---------- Email ----------
    email_send_enabled: bool = False
    email_verification_token_expire_hours: int = 24
    password_reset_token_expire_minutes: int = 30
    frontend_url: str = "http://localhost:8000"

    # ---------- Tests ----------
    test_database_name: str = "bookdealers_test"

    @property
    def database_url(self) -> str:
        """Construeix l'URL de connexió a la base de dades."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def test_database_url(self) -> str:
        """URL de la base de dades de tests (mateix servidor, altre schema/db)."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.test_database_name}"
        )


# Instància singleton de la configuració
settings = Settings()
