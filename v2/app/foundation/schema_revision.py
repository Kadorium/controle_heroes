"""Schema revision gate — ORM/código espera alembic 026 (L-006 + tax_id)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Head canônico da árvore em execução. Migration 020 (RUX-3A Catalog) vive em WIP isolado — não aplicar.
EXPECTED_ALEMBIC_REVISION = "026"


class SchemaRevisionDriftError(RuntimeError):
    """Aplicado ≠ esperado — API não deve subir silenciosamente."""


def get_applied_alembic_revision(db: Session) -> str | None:
    try:
        row = db.execute(text("SELECT version_num FROM alembic_version")).fetchone()
    except Exception:
        return None
    if not row:
        return None
    return str(row[0])


def assert_schema_revision(db: Session, *, expected: str = EXPECTED_ALEMBIC_REVISION) -> str:
    """Falha alto se o head aplicado ≠ esperado pelo código."""
    applied = get_applied_alembic_revision(db)
    if applied is None:
        raise SchemaRevisionDriftError(
            f"alembic_version ausente ou ilegível; esperado={expected}"
        )
    if applied != expected:
        raise SchemaRevisionDriftError(
            f"Schema drift: alembic aplicado={applied} esperado_pelo_codigo={expected}. "
            "Não subir em drift. Migration 020 (RUX-3A) não deve ser aplicada."
        )
    return applied
