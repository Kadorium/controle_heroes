"""Erros de domínio Customs — sem HTTP."""


class CustomsError(Exception):
    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class ProcessNotFound(CustomsError):
    def __init__(self, process_id: int | str):
        super().__init__(f"ImportProcess {process_id} não encontrado", code="process_not_found")


class ProcessConflict(CustomsError):
    def __init__(self):
        super().__init__("Versão desatualizada — recarregue o processo", code="conflict")


class ProcessValidationError(CustomsError):
    def __init__(self, message: str, *, code: str = "validation_error"):
        super().__init__(message, code=code)


class ProcessNotDraft(CustomsError):
    def __init__(self, message: str = "Somente processo DRAFT permite esta alteração"):
        super().__init__(message, code="process_not_draft")


class ProcessImmutable(CustomsError):
    def __init__(self, message: str = "Processo não permite alteração estrutural"):
        super().__init__(message, code="process_immutable")


class OverAllocationError(CustomsError):
    def __init__(self, message: str = "Quantidade excede residual disponível"):
        super().__init__(message, code="over_allocation")


class DoganaleNotFound(CustomsError):
    def __init__(self, ref: int | str):
        super().__init__(f"Doganale {ref} não encontrada", code="doganale_not_found")


class DoganaleVersionNotFound(CustomsError):
    def __init__(self, version_id: int | str):
        super().__init__(
            f"Versão Doganale {version_id} não encontrada", code="doganale_version_not_found"
        )


class DoganaleConflict(CustomsError):
    def __init__(self):
        super().__init__("Versão Doganale desatualizada — recarregue", code="conflict")


class DoganaleImmutable(CustomsError):
    def __init__(self, message: str = "Versão Doganale imutável"):
        super().__init__(message, code="doganale_immutable")


class DoganaleValidationError(CustomsError):
    def __init__(self, message: str, *, code: str = "validation_error"):
        super().__init__(message, code=code)


class PayeeNotFound(CustomsError):
    def __init__(self, payee_id: int | str):
        super().__init__(f"CustomsPayee {payee_id} não encontrado", code="payee_not_found")


class PayeeValidationError(CustomsError):
    def __init__(self, message: str, *, code: str = "validation_error"):
        super().__init__(message, code=code)


class FundingNotFound(CustomsError):
    def __init__(self, funding_id: int | str):
        super().__init__(
            f"FundingRequest {funding_id} não encontrado", code="funding_not_found"
        )


class FundingConflict(CustomsError):
    def __init__(self):
        super().__init__("FundingRequest desatualizado — recarregue", code="conflict")


class FundingImmutable(CustomsError):
    def __init__(self, message: str = "FundingRequest imutável"):
        super().__init__(message, code="funding_immutable")


class FundingValidationError(CustomsError):
    def __init__(self, message: str, *, code: str = "validation_error"):
        super().__init__(message, code=code)


class NationalizationNotFound(CustomsError):
    def __init__(self, nat_id: int | str):
        super().__init__(
            f"Nationalization {nat_id} não encontrada", code="nationalization_not_found"
        )


class NationalizationConflict(CustomsError):
    def __init__(self):
        super().__init__("Nationalization desatualizada — recarregue", code="conflict")


class NationalizationImmutable(CustomsError):
    def __init__(self, message: str = "Nationalization imutável"):
        super().__init__(message, code="nationalization_immutable")


class NationalizationValidationError(CustomsError):
    def __init__(self, message: str, *, code: str = "validation_error"):
        super().__init__(message, code=code)


class OverNationalizationError(CustomsError):
    def __init__(self, message: str = "Quantidade excede residual nacionalizável"):
        super().__init__(message, code="over_nationalization")

