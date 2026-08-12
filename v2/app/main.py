"""ASGI entrypoint: uvicorn app.main:app --app-dir v2 (CWD=v2)."""

from app.foundation.create_app import app

__all__ = ["app"]

