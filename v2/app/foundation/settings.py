from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Epic Controle V2"
    app_env: str = "development"
    secret_key: str = "dev-secret-v2"
    host: str = "0.0.0.0"
    port: int = 8081
    database_url: str = "postgresql://postgres@localhost:5433/epic_v2"
    attachments_path: Path = ROOT_DIR / "data" / "attachments"
    logs_path: Path = ROOT_DIR / "logs"
    frontend_dist_path: Path = ROOT_DIR / "frontend" / "dist"
    session_cookie_name: str = "epic_v2_session"
    session_max_age_seconds: int = 86400
    seed_admin_email: str = "admin@epic.com.br"
    seed_admin_password: str = "admin123"
    seed_admin_name: str = "Administrador"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def ensure_runtime_dirs(settings: Settings | None = None) -> None:
    s = settings or get_settings()
    for path in (s.attachments_path, s.logs_path):
        path.mkdir(parents=True, exist_ok=True)
