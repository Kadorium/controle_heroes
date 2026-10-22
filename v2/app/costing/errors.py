"""Costing errors."""


class CostingError(Exception):
    def __init__(self, message: str, code: str = "costing_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class CostingNotFound(CostingError):
    def __init__(self, entity: str, ident):
        super().__init__(f"{entity} {ident} não encontrado", code="not_found")


class CostingConflict(CostingError):
    def __init__(self, message: str, code: str = "conflict"):
        super().__init__(message, code=code)


class CostingValidation(CostingError):
    def __init__(self, message: str, code: str = "validation_error"):
        super().__init__(message, code=code)


class PublishBlocked(CostingError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, code="publish_blocked")
        self.details = details or {}
