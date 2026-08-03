"""Inventory errors — I5-4."""

from __future__ import annotations


class InventoryError(Exception):
    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class InventoryNotImplemented(InventoryError):
    """Legacy stub — retained for import compatibility; unused after I5-4."""

    def __init__(self, capability: str):
        super().__init__(
            f"Inventory capability '{capability}' not implemented until later I5 checkpoint",
            code="inventory_not_implemented",
        )


class LocationNotFound(InventoryError):
    def __init__(self, ref: int | str):
        super().__init__(f"StockLocation {ref} não encontrada", code="location_not_found")


class ReceiptNotFound(InventoryError):
    def __init__(self, receipt_id: int | str):
        super().__init__(f"GoodsReceipt {receipt_id} não encontrado", code="receipt_not_found")


class ReceiptConflict(InventoryError):
    def __init__(self):
        super().__init__("GoodsReceipt desatualizado — recarregue", code="conflict")


class ReceiptImmutable(InventoryError):
    def __init__(self, message: str = "GoodsReceipt imutável"):
        super().__init__(message, code="receipt_immutable")


class InventoryValidationError(InventoryError):
    def __init__(self, message: str, *, code: str = "validation_error"):
        super().__init__(message, code=code)


class NationalizationRequired(InventoryError):
    def __init__(self, message: str = "Recebimento doméstico exige nacionalização prévia"):
        super().__init__(message, code="nationalization_required")


class OverReceiptError(InventoryError):
    def __init__(self, message: str = "Quantidade excede residual nacionalizado disponível"):
        super().__init__(message, code="over_receipt")
