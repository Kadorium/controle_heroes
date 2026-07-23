class TreasuryError(Exception):
    code = "treasury_error"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class PaymentNotFound(TreasuryError):
    code = "payment_not_found"

    def __init__(self, payment_id: int):
        super().__init__(f"Pagamento #{payment_id} não encontrado")


class PaymentConflict(TreasuryError):
    code = "conflict"

    def __init__(self, message: str = "Conflito de versão do pagamento"):
        super().__init__(message, code="conflict")


class PaymentValidationError(TreasuryError):
    code = "validation_error"


class InvalidTransition(TreasuryError):
    code = "invalid_transition"
