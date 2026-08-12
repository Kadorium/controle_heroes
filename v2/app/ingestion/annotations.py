"""Anotações FreeText — extração de origem China/Italy do campo layout PDF.

Padrão observado nos corpus 202: o campo "Country of origin/acquisition" no modo
layout apresenta "chinaItaly" (sem espaço), indicando duas camadas de texto no PDF.
Decisão P0: extrair ambas; preferência = valor declarado ("Italy"); emitir issue DUAL_ORIGIN.

Funções puras — sem I/O, sem ORM.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class OriginAnnotation:
    raw_value: str | None
    declared: str | None
    possible_other: str | None
    locator_json: str | None


_RE_ORIGIN = re.compile(
    r"Country\s+of\s+origin(?:/acquisition)?\s*:?\s*(\S+(?:[^\S\n]+\S+)?)",
    re.IGNORECASE,
)

# Known dual-layer patterns where PDF overlays two text strings
_DUAL_PATTERNS: list[tuple[str, str]] = [
    ("china", "Italy"),
    ("China", "Italy"),
]


def extract_origin_annotation(layout_text: str) -> OriginAnnotation:
    """Extrai anotação de origem do texto em modo layout.

    Detecta o padrão 'chinaItaly' (duas camadas sobrepostas no PDF) e retorna:
    - raw_value: o que aparece no PDF (e.g. "chinaItaly")
    - declared: o valor declarado preferencial (e.g. "Italy")
    - possible_other: o valor de fundo detectado (e.g. "china")
    """
    import json

    m = _RE_ORIGIN.search(layout_text)
    if not m:
        return OriginAnnotation(
            raw_value=None,
            declared=None,
            possible_other=None,
            locator_json=None,
        )

    raw = m.group(1).strip()
    locator = json.dumps({"field": "origin_country", "source": "layout_freetext"})

    # Detect dual-layer: "chinaItaly", "ChinaItaly", etc.
    declared: str | None = raw
    possible_other: str | None = None

    for bg, fg in _DUAL_PATTERNS:
        # Glued: "chinaItaly" → bg="china", fg="Italy"
        if raw.lower() == (bg + fg).lower() or raw == bg + fg:
            declared = fg
            possible_other = bg
            break
        # Or space-separated "china Italy"
        if raw.lower() == f"{bg.lower()} {fg.lower()}":
            declared = fg
            possible_other = bg
            break
        # Just "Italy" (single layer, clean)
        if raw.strip().lower() == fg.lower():
            declared = fg
            possible_other = None
            break

    return OriginAnnotation(
        raw_value=raw,
        declared=declared,
        possible_other=possible_other,
        locator_json=locator,
    )
