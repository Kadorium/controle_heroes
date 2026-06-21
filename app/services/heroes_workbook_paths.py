"""Resolução de caminhos da planilha legada Heroes."""

from __future__ import annotations

from pathlib import Path

from app.config import ROOT_DIR

HEROES_WORKBOOK_FILENAME = "CONTI ITALIA-BRASILE.xlsx"

SEARCH_PATHS = (
    ROOT_DIR / HEROES_WORKBOOK_FILENAME,
    ROOT_DIR / "data" / "raw" / HEROES_WORKBOOK_FILENAME,
)


def resolve_heroes_workbook_path(explicit: Path | str | None = None) -> Path | None:
    """Retorna o primeiro caminho existente na ordem: explícito → raiz → data/raw."""
    if explicit is not None:
        p = Path(explicit)
        if p.is_file():
            return p.resolve()
    for candidate in SEARCH_PATHS:
        if candidate.is_file():
            return candidate.resolve()
    return None


def heroes_workbook_search_labels() -> list[str]:
    return [str(p.relative_to(ROOT_DIR)) if p.is_relative_to(ROOT_DIR) else str(p) for p in SEARCH_PATHS]
