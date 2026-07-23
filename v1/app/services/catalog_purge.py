"""Exclusão física de cadastros anulados — ambiente dev/test."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Credit,
    HeroesDispatchPendingItem,
    ImportationItem,
    ImportationOrder,
    InvoiceItem,
    Product,
    Supplier,
)


def _product_blockers(db: Session, product_id: int) -> list[str]:
    blockers: list[str] = []
    if db.query(ImportationItem).filter(ImportationItem.product_id == product_id).first():
        blockers.append("itens de importação")
    if db.query(InvoiceItem).filter(InvoiceItem.product_id == product_id).first():
        blockers.append("itens de fatura")
    if db.query(HeroesDispatchPendingItem).filter(HeroesDispatchPendingItem.product_id == product_id).first():
        blockers.append("pendências Heroes")
    return blockers


def _supplier_blockers(db: Session, supplier_id: int) -> list[str]:
    blockers: list[str] = []
    if db.query(ImportationOrder).filter(ImportationOrder.supplier_id == supplier_id).first():
        blockers.append("ordens de importação")
    if db.query(Product).filter(Product.default_supplier_id == supplier_id).first():
        blockers.append("produtos com fornecedor padrão")
    if db.query(Credit).filter(Credit.supplier_id == supplier_id).first():
        blockers.append("créditos")
    return blockers


def delete_cancelled_products(db: Session, product_ids: list[int]) -> int:
    if not product_ids:
        return 0
    removed = 0
    for pid in product_ids:
        product = (
            db.query(Product)
            .filter(Product.id == pid, Product.is_active.is_(False))
            .first()
        )
        if not product:
            raise ValueError(f"Produto id={pid} não encontrado ou ainda ativo")
        blockers = _product_blockers(db, pid)
        if blockers:
            raise ValueError(
                f"Produto «{product.sku_code}» ainda referenciado em: {', '.join(blockers)}. "
                "Exclua as ordens vinculadas antes."
            )
        db.delete(product)
        removed += 1
    return removed


def delete_cancelled_suppliers(db: Session, supplier_ids: list[int]) -> int:
    if not supplier_ids:
        return 0
    removed = 0
    for sid in supplier_ids:
        supplier = (
            db.query(Supplier)
            .filter(Supplier.id == sid, Supplier.is_active.is_(False))
            .first()
        )
        if not supplier:
            raise ValueError(f"Fornecedor id={sid} não encontrado ou ainda ativo")
        blockers = _supplier_blockers(db, sid)
        if blockers:
            raise ValueError(
                f"Fornecedor «{supplier.name}» ainda referenciado em: {', '.join(blockers)}. "
                "Exclua ordens e vínculos antes."
            )
        db.delete(supplier)
        removed += 1
    return removed
