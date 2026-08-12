"""Trilha de falha de commit (RUX-2R-b / DEC-RUX-TX-02).

O commit de Ordine e Fattura é tudo-ou-nada: qualquer operação que falhe derruba
a transação inteira. O rollback também apagaria o ledger da tentativa, que é
justamente o que o operador precisa ler. Por isso a trilha é gravada FORA da
transação de negócio, em sessão própria, depois do rollback.

Como nada de domínio sobrevive a uma tentativa falhada, o retry com a mesma
operation_key reexecuta do zero (ver ``execute_commit``).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from app.audit import public as audit_public
from app.foundation.database import SessionLocal
from app.ingestion.commit_models import IngestionCommitAttempt, IngestionCommitOperation
from app.ingestion.errors import IngestionError

ROLLED_BACK_REASON = "revertido pelo rollback all-or-nothing"


def reset_attempt_ledger(db, attempt: IngestionCommitAttempt) -> None:
    """Limpa o ledger de uma tentativa anterior — o retry reexecuta tudo do zero."""
    db.query(IngestionCommitOperation).filter(
        IngestionCommitOperation.attempt_id == attempt.id
    ).delete(synchronize_session=False)
    attempt.status = "UNKNOWN"
    db.flush()


@dataclass
class CommitFailureTrail:
    """Dados da falha capturados na sessão de negócio, antes do rollback."""

    document_id: int
    operation_key: str
    payload_fingerprint: str
    actor_id: str
    failed_op_key: str | None
    error_message: str
    rolled_back_ops: list[str] = field(default_factory=list)
    context: dict = field(default_factory=dict)


def snapshot_attempt_failure(
    attempt: IngestionCommitAttempt,
    *,
    failed_op_key: str | None = None,
    error_message: str | None = None,
    context: dict | None = None,
) -> CommitFailureTrail:
    """Lê o attempt ainda na sessão de negócio e devolve dados puros para a trilha."""
    failed_key = failed_op_key
    message = error_message
    rolled_back: list[str] = []
    for op in attempt.operations or []:
        if op.status == "FAILED":
            if failed_key is None:
                failed_key = op.op_key
                message = message or op.error_message
        elif op.status == "SUCCEEDED":
            rolled_back.append(op.op_key)
    return CommitFailureTrail(
        document_id=attempt.document_id,
        operation_key=attempt.operation_key,
        payload_fingerprint=attempt.payload_fingerprint,
        actor_id=attempt.actor_id or "",
        failed_op_key=failed_key,
        error_message=message or "commit revertido: nenhuma operação persistida",
        rolled_back_ops=rolled_back,
        context=dict(context or {}),
    )


class CommitOperationFailed(IngestionError):
    """Uma operação owner falhou — a transação inteira deve ser revertida.

    Carrega a trilha já montada em memória, para a route gravá-la fora da
    transação mesmo quando a sessão está inutilizável por erro de banco.
    """

    def __init__(self, op_key: str, error_message: str, *, trail: CommitFailureTrail) -> None:
        super().__init__(
            f"Operação '{op_key}' falhou: {error_message}",
            code="commit_operation_failed",
        )
        self.op_key = op_key
        self.error_message = error_message
        self.trail = trail


def record_commit_failure(trail: CommitFailureTrail) -> int:
    """Grava attempt FAILED + ledger + Audit em sessão separada. Retorna o attempt_id."""
    session = SessionLocal()
    try:
        attempt = (
            session.query(IngestionCommitAttempt)
            .filter(IngestionCommitAttempt.operation_key == trail.operation_key)
            .first()
        )
        if attempt is None:
            attempt = IngestionCommitAttempt(
                document_id=trail.document_id,
                operation_key=trail.operation_key,
                payload_fingerprint=trail.payload_fingerprint,
                status="FAILED",
                actor_id=trail.actor_id or None,
            )
            session.add(attempt)
            session.flush()
        else:
            attempt.payload_fingerprint = trail.payload_fingerprint
            attempt.status = "FAILED"
            attempt.actor_id = trail.actor_id or attempt.actor_id
            session.query(IngestionCommitOperation).filter(
                IngestionCommitOperation.attempt_id == attempt.id
            ).delete(synchronize_session=False)
            session.flush()

        for op_key in trail.rolled_back_ops:
            if op_key == trail.failed_op_key:
                continue
            session.add(
                IngestionCommitOperation(
                    attempt_id=attempt.id,
                    op_key=op_key,
                    status="SKIPPED",
                    details_json=json.dumps(
                        {"rolled_back": True, "reason": ROLLED_BACK_REASON},
                        ensure_ascii=False,
                    ),
                )
            )
        if trail.failed_op_key:
            session.add(
                IngestionCommitOperation(
                    attempt_id=attempt.id,
                    op_key=trail.failed_op_key,
                    status="FAILED",
                    error_message=(trail.error_message or "")[:512],
                )
            )
        session.flush()

        audit_public.record_event(
            session,
            actor_id=trail.actor_id or None,
            entity_type="ingestion_commit_attempt",
            entity_id=str(attempt.id),
            action="commit_failed",
            reason_code="INGEST_COMMIT_FAILED",
            details=json.dumps(
                {
                    "document_id": trail.document_id,
                    "failed_op": trail.failed_op_key,
                    "error": (trail.error_message or "")[:512],
                    "rolled_back_ops": trail.rolled_back_ops,
                    **trail.context,
                },
                ensure_ascii=False,
            ),
        )
        session.commit()
        return attempt.id
    finally:
        session.close()
