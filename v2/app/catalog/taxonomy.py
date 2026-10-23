"""Taxonomia comercial 3 categorias × 8 tipos. Seeds idempotentes."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.catalog.models import ProductCategory, ProductType

CATEGORIES: tuple[tuple[str, str, int], ...] = (
    ("Raquetes", "raquetes", 1),
    ("Acessórios", "acessorios", 2),
    ("Vestuário", "vestuario", 3),
)

SUBCATEGORIES: dict[str, tuple[str, ...]] = {
    "raquetes": ("Beach Tennis", "Padel", "Pickleball"),
    "acessorios": (
        "Bolsas e raqueteiras",
        "Mochilas",
        "Malas",
        "Consumíveis",
        "Equipamento",
        "Acessório de vestuário",
    ),
    "vestuario": (),
}

PRODUCT_TYPES: tuple[tuple[str, str, int, tuple[str, ...]], ...] = (
    ("Raquete", "raquete", 1, ("sport", "model", "collection_year")),
    ("Bolsa", "bolsa", 2, ("line", "collection_year")),
    ("Mochila", "mochila", 3, ("line", "collection_year")),
    ("Mala", "mala", 4, ("line", "collection_year")),
    ("Consumível", "consumivel", 5, ("sport", "pack_qty", "consumable_kind")),
    ("Equipamento", "equipamento", 6, ("sport",)),
    ("Acessório de vestuário", "acessorio-de-vestuario", 7, ("line", "sport")),
    ("Vestuário", "vestuario", 8, ("garment_kind", "gender")),
)

ATTR_KEYS = (
    "sport",
    "line",
    "model",
    "collection_year",
    "garment_kind",
    "gender",
    "pack_qty",
    "consumable_kind",
)

TAXONOMY_STATUSES = ("CONFIDENT", "REVIEW")
LIFECYCLE_STATUSES = ("ACTIVE", "DISCONTINUED", "UNKNOWN")
IMPORT_DECISIONS = ("APROVAR", "EDITAR", "REVISAR", "IGNORAR")
SOURCE_KINDS = ("manual", "heroes_csv")

PROV_CSV = "csv_historical"
PROV_RULE = "deterministic_rule"
PROV_MANUAL = "manual"
PROV_BATCH = "import_batch"
PROV_ABSENT = "absent"

PROVENANCE_LABELS = {
    PROV_CSV: "Catálogo histórico (planilha Heroes)",
    PROV_RULE: "Classificação proposta a partir do histórico",
    PROV_MANUAL: "Edição manual",
    PROV_BATCH: "Importação do lote de revisão",
    PROV_ABSENT: "Não informado",
}


def ensure_taxonomy(db: Session) -> None:
    """Insert 3 categories + 8 types if missing. Safe to re-run."""
    existing_cats = {row.slug: row for row in db.query(ProductCategory).all()}
    for name, slug, position in CATEGORIES:
        if slug in existing_cats:
            row = existing_cats[slug]
            row.name = name
            row.position = position
            continue
        row = ProductCategory(name=name, slug=slug, parent_id=None, position=position)
        db.add(row)
        existing_cats[slug] = row
    db.flush()

    existing_types = {row.slug: row for row in db.query(ProductType).all()}
    for name, slug, position, attrs in PRODUCT_TYPES:
        payload = list(attrs)
        if slug in existing_types:
            row = existing_types[slug]
            row.name = name
            row.position = position
            row.recommended_attributes = payload
            continue
        db.add(
            ProductType(
                name=name,
                slug=slug,
                position=position,
                recommended_attributes=payload,
            )
        )
    db.flush()


def category_by_name(db: Session, name: str) -> ProductCategory | None:
    return db.query(ProductCategory).filter(ProductCategory.name == name).first()


def type_by_name(db: Session, name: str) -> ProductType | None:
    return db.query(ProductType).filter(ProductType.name == name).first()


def allowed_subcategories(category_slug: str | None) -> tuple[str, ...]:
    if not category_slug:
        return ()
    return SUBCATEGORIES.get(category_slug, ())
