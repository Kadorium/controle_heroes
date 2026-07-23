from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent

# Moeda padrão das importações Epic (fornecedores italianos / Heroes).
DEFAULT_IMPORT_CURRENCY = "EUR"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Epic Importações"
    app_env: str = "development"
    secret_key: str = "dev-secret-change-in-production"
    host: str = "0.0.0.0"
    port: int = 8080

    database_url: str = "postgresql://postgres@localhost:5433/epic_importacao"

    attachments_path: Path = ROOT_DIR / "data" / "attachments"
    imports_path: Path = ROOT_DIR / "data" / "imports"
    backups_db_path: Path = ROOT_DIR / "backups" / "db"
    backups_attachments_path: Path = ROOT_DIR / "backups" / "attachments"
    logs_path: Path = ROOT_DIR / "logs"
    frontend_dist_path: Path = ROOT_DIR / "frontend" / "dist"

    session_cookie_name: str = "epic_session"
    session_max_age_seconds: int = 86400

    seed_admin_email: str = "admin@epic.com.br"
    seed_admin_password: str = "admin123"
    seed_admin_name: str = "Administrador"

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in ("development", "dev", "local")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_runtime_dirs(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    for path in (
        s.attachments_path,
        s.imports_path,
        s.backups_db_path,
        s.backups_attachments_path,
        s.logs_path,
    ):
        path.mkdir(parents=True, exist_ok=True)
