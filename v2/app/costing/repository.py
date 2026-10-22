"""Costing persistence."""

from sqlalchemy.orm import Session

from app.costing.models import (
    CostAllocation,
    CostComponent,
    CostingCase,
    CostingExpense,
    CostingLine,
    CostingVersion,
)


def get_case(db: Session, case_id: int) -> CostingCase | None:
    return db.query(CostingCase).filter(CostingCase.id == case_id).first()


def get_case_by_process(db: Session, process_id: int) -> CostingCase | None:
    return db.query(CostingCase).filter(CostingCase.import_process_id == process_id).first()


def get_version(db: Session, version_id: int) -> CostingVersion | None:
    return db.query(CostingVersion).filter(CostingVersion.id == version_id).first()


def list_versions(db: Session, case_id: int) -> list[CostingVersion]:
    return (
        db.query(CostingVersion)
        .filter(CostingVersion.case_id == case_id)
        .order_by(CostingVersion.version_number.desc())
        .all()
    )


def next_version_number(db: Session, case_id: int) -> int:
    row = (
        db.query(CostingVersion.version_number)
        .filter(CostingVersion.case_id == case_id)
        .order_by(CostingVersion.version_number.desc())
        .first()
    )
    return (row[0] + 1) if row else 1


def get_draft(db: Session, case_id: int, kind: str) -> CostingVersion | None:
    return (
        db.query(CostingVersion)
        .filter(
            CostingVersion.case_id == case_id,
            CostingVersion.kind == kind,
            CostingVersion.status == "DRAFT",
        )
        .order_by(CostingVersion.version_number.desc())
        .first()
    )


def list_cases(db: Session, *, limit: int = 100, offset: int = 0) -> list[CostingCase]:
    return (
        db.query(CostingCase)
        .order_by(CostingCase.updated_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_expense(db: Session, expense_id: int) -> CostingExpense | None:
    return db.query(CostingExpense).filter(CostingExpense.id == expense_id).first()


def delete_version_children(db: Session, version: CostingVersion) -> None:
    for line in list(version.lines):
        db.delete(line)
    for comp in list(version.components):
        db.delete(comp)
    db.flush()
