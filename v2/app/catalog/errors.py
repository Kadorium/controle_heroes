"""Erros de domínio Catalog — sem HTTP."""


class CatalogError(Exception):
    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class SupplierNotFound(CatalogError):
    def __init__(self, supplier_id: int):
        super().__init__(f"Supplier {supplier_id} não encontrado", code="supplier_not_found")


class ProductNotFound(CatalogError):
    def __init__(self, key: str | int):
        super().__init__(f"Product {key} não encontrado", code="product_not_found")


class SkuDuplicate(CatalogError):
    def __init__(self, sku: str):
        super().__init__(f"SKU já existe: {sku}", code="sku_duplicate")


class SupplierCodeDuplicate(CatalogError):
    def __init__(self, code: str):
        super().__init__(f"Código de fornecedor já existe: {code}", code="supplier_code_duplicate")


class CatalogValidationError(CatalogError):
    def __init__(self, message: str):
        super().__init__(message, code="validation_error")
