"""Normalização Catalog — local ao módulo (ADR-14: Catalog ↛ Orders).

CSV controlado = FUTURO (Blueprint §5.5). Não implementar import nesta campanha.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
import re

from app.catalog.errors import CatalogValidationError

_WS_RE = re.compile(r"\s+")
_NON_DIGIT_RE = re.compile(r"\D+")


def normalize_free_text(value: str | None, *, max_len: int = 64) -> str | None:
    if value is None:
        return None
    s = _WS_RE.sub(" ", str(value).strip())
    if not s:
        return None
    if len(s) > max_len:
        raise CatalogValidationError(f"Texto excede {max_len} caracteres")
    return s


def normalize_country(value: str | None) -> str | None:
    if value is None:
        return None
    s = str(value).strip().upper()
    if not s:
        return None
    if len(s) != 2 or not s.isalpha():
        raise CatalogValidationError("País deve ter 2 letras ISO")
    return s


def normalize_unit(value: str | None) -> str | None:
    """Unidade documental (PZ, SET, CTNS, UN, KG, MT, LT, CF). Sem tabela UoM."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    if len(s) > 16:
        raise CatalogValidationError("Unidade máximo 16 caracteres")
    return s.upper()


def normalize_digits_id(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    digits = _NON_DIGIT_RE.sub("", raw)
    if not digits:
        raise CatalogValidationError("Informe apenas dígitos")
    if digits != raw.replace(" ", "").replace(".", "").replace("-", "").replace("/", ""):
        # punctuation stripped is OK; leftover letters after strip of IT prefix handled elsewhere
        pass
    return digits


def normalize_ncm(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    digits = _NON_DIGIT_RE.sub("", raw)
    if not digits:
        raise CatalogValidationError("NCM inválido")
    if len(digits) != 8:
        raise CatalogValidationError("NCM deve ter 8 dígitos")
    return digits


def normalize_ean(value: str | None) -> str | None:
    """Dígitos only; comprimento 8–14 é aviso de UI — API rejeita só não-dígito."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    if re.search(r"[^\d\s]", raw):
        digits = _NON_DIGIT_RE.sub("", raw)
        if not digits:
            raise CatalogValidationError("EAN deve conter apenas dígitos")
        return digits
    digits = raw.replace(" ", "")
    if not digits.isdigit():
        raise CatalogValidationError("EAN deve conter apenas dígitos")
    return digits


def normalize_tax_id(value: str | None, *, country_code: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    s = raw.upper()
    if (country_code or "").upper() == "IT" or s.startswith("IT"):
        if s.startswith("IT"):
            s = s[2:]
    digits = _NON_DIGIT_RE.sub("", s)
    if not digits:
        raise CatalogValidationError("Identificador fiscal inválido")
    return digits


def normalize_weight(value: object | None) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        n = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise CatalogValidationError("Peso inválido") from exc
    if n <= 0:
        raise CatalogValidationError("Peso deve ser maior que zero")
    return n
