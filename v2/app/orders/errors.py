"""Erros de domínio Orders — sem HTTP."""


class OrdersError(Exception):
    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class OrderNotFound(OrdersError):
    def __init__(self, order_id: int):
        super().__init__(f"Order {order_id} não encontrada", code="order_not_found")


class OrderNotDraft(OrdersError):
    def __init__(self):
        super().__init__("Ordem só pode ser editada em DRAFT", code="order_not_draft")


class OrderConflict(OrdersError):
    def __init__(self):
        super().__init__("Versão desatualizada — recarregue a ordem", code="conflict")


class OrderValidationError(OrdersError):
    def __init__(self, message: str, *, code: str = "validation_error"):
        super().__init__(message, code=code)


class OrderItemNotFound(OrdersError):
    def __init__(self, item_id: int):
        super().__init__(f"Item {item_id} não encontrado", code="order_item_not_found")


class InvalidTransition(OrdersError):
    def __init__(self, message: str):
        super().__init__(message, code="invalid_transition")
