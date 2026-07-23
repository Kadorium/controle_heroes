"""Unit of Work — uma Session, um commit para ação crítica + Audit."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session

from app.foundation.database import SessionLocal


class UnitOfWork:
    def __init__(self, session: Session | None = None) -> None:
        self._owned = session is None
        self.session = session or SessionLocal()

    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.session.rollback()
        if self._owned:
            self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
