"""Erros de domínio Logistics — sem HTTP."""


class LogisticsError(Exception):
    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class ShipmentNotFound(LogisticsError):
    def __init__(self, shipment_id: int | str):
        super().__init__(f"Shipment {shipment_id} não encontrado", code="shipment_not_found")


class ShipmentConflict(LogisticsError):
    def __init__(self):
        super().__init__("Versão desatualizada — recarregue o embarque", code="conflict")


class ShipmentValidationError(LogisticsError):
    def __init__(self, message: str, *, code: str = "validation_error"):
        super().__init__(message, code=code)


class OvershipError(LogisticsError):
    def __init__(self, message: str = "Quantidade excede residual do OrderItem"):
        super().__init__(message, code="overship")


class InvalidTransition(LogisticsError):
    def __init__(self, message: str):
        super().__init__(message, code="invalid_transition")


class ShipmentNotPlanned(LogisticsError):
    def __init__(self, message: str = "Operação só permitida em PLANNED"):
        super().__init__(message, code="shipment_not_planned")


class ProviderNotFound(LogisticsError):
    def __init__(self, provider_id: int | str):
        super().__init__(
            f"Prestador logístico {provider_id} não encontrado",
            code="provider_not_found",
        )
