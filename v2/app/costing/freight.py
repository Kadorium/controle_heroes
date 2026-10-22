"""Papéis semânticos de frete — ValueBasis CIF nunca é componente.

Não classificar por substring genérica «FRETE». A decisão é o papel:
- CUSTOMS_BASIS: base CIF aduaneira (ValueBasis FRETE)
- INTERNATIONAL: FRETE INTERNACIONAL (despesa Bechtrans / agente)
- DOMESTIC_REMOVAL / DOMESTIC_DELIVERY: logística doméstica
"""

from __future__ import annotations

import re
import unicodedata

ROLE_CUSTOMS_BASIS = "CUSTOMS_BASIS"
ROLE_INTERNATIONAL = "INTERNATIONAL"
ROLE_DOMESTIC_REMOVAL = "DOMESTIC_REMOVAL"
ROLE_DOMESTIC_DELIVERY = "DOMESTIC_DELIVERY"

_COMPONENT_TYPE = {
    ROLE_INTERNATIONAL: "FRETE_INTERNACIONAL",
    ROLE_DOMESTIC_REMOVAL: "FRETE_REMOCAO",
    ROLE_DOMESTIC_DELIVERY: "FRETE_ENTREGA",
}

_INTERNATIONAL_CODES = frozenset({"FRETE_INT", "FRETE_INTERNACIONAL", "FREIGHT_INT", "FREIGHT_INTERNATIONAL"})


def normalize_freight_token(code: str | None, label: str | None) -> str:
    blob = f"{code or ''} {label or ''}"
    nfkd = unicodedata.normalize("NFKD", blob)
    ascii_ = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"[^A-Z0-9]+", "_", ascii_.upper()).strip("_")


def classify_freight_role(
    code: str | None,
    label: str | None,
    *,
    source: str,
) -> str | None:
    token = normalize_freight_token(code, label)
    if not token:
        return None
    code_n = normalize_freight_token(code, None)
    if "INTERNACIONAL" in token or "INTERNATIONAL" in token or code_n in _INTERNATIONAL_CODES:
        return ROLE_INTERNATIONAL
    if "REMOCAO" in token or "REMOVAL" in token:
        return ROLE_DOMESTIC_REMOVAL
    if "ENTREGA" in token or "DELIVERY" in token:
        return ROLE_DOMESTIC_DELIVERY
    if source == "value_basis" and "FRETE" in token:
        return ROLE_CUSTOMS_BASIS
    return None


def component_type_for_role(role: str | None, *, fallback_code: str | None, fallback_label: str | None) -> str:
    if role and role in _COMPONENT_TYPE:
        return _COMPONENT_TYPE[role]
    raw = (fallback_code or fallback_label or "DESPESA").upper().replace(" ", "_")
    return raw[:64]


def is_customs_freight_basis(code: str | None, label: str | None) -> bool:
    return classify_freight_role(code, label, source="value_basis") == ROLE_CUSTOMS_BASIS


def is_international_freight(code: str | None, label: str | None) -> bool:
    return classify_freight_role(code, label, source="expense") == ROLE_INTERNATIONAL
