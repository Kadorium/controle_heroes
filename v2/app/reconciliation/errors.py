"""Reconciliation errors."""


class ReconciliationError(Exception):
    def __init__(self, message: str, code: str = "reconciliation_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class PairNotFound(ReconciliationError):
    def __init__(self, pair_id: int):
        super().__init__(f"Par {pair_id} não encontrado", code="not_found")


class PairConflict(ReconciliationError):
    def __init__(self, message: str, code: str = "conflict"):
        super().__init__(message, code=code)
