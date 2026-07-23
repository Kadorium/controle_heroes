class BillingError(Exception):
    code = "billing_error"

    def __init__(self, message: str, *, code: str | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class InvoiceNotFound(BillingError):
    code = "invoice_not_found"

    def __init__(self, invoice_id: int):
        super().__init__(f"Fatura #{invoice_id} não encontrada")


class InvoiceNotDraft(BillingError):
    code = "invoice_not_draft"

    def __init__(self):
        super().__init__("Somente faturas em rascunho podem ser alteradas", code="invoice_not_draft")


class InvoiceConflict(BillingError):
    code = "conflict"

    def __init__(self):
        super().__init__("Conflito de versão da fatura", code="conflict")


class InvoiceValidationError(BillingError):
    code = "validation_error"


class InvalidTransition(BillingError):
    code = "invalid_transition"


class PayableNotFound(BillingError):
    code = "payable_not_found"

    def __init__(self, payable_id: int):
        super().__init__(f"Payable #{payable_id} não encontrado")


class PayableConflict(BillingError):
    code = "conflict"

    def __init__(self, payable_id: int | None = None):
        msg = (
            f"Conflito de versão do payable #{payable_id}"
            if payable_id
            else "Conflito de versão do payable"
        )
        super().__init__(msg, code="conflict")


class PayableValidationError(BillingError):
    code = "validation_error"
