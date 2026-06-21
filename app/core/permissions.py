"""Permissões por ação crítica — expandir nas fases seguintes."""

# Módulo
PERM_USERS_READ = "users:read"
PERM_USERS_WRITE = "users:write"
PERM_IMPORTATION_READ = "importation:read"
PERM_IMPORTATION_WRITE = "importation:write"
PERM_FINANCE_READ = "finance:read"
PERM_FINANCE_WRITE = "finance:write"
PERM_DOCUMENTS_READ = "documents:read"
PERM_DOCUMENTS_WRITE = "documents:write"
PERM_IMPORTS_READ = "imports:read"
PERM_IMPORTS_WRITE = "imports:write"
PERM_IMPORTS_APPROVE = "imports:approve"
PERM_LOGISTICS_READ = "logistics:read"
PERM_LOGISTICS_WRITE = "logistics:write"
PERM_CUSTOMS_READ = "customs:read"
PERM_CUSTOMS_WRITE = "customs:write"
PERM_STOCK_READ = "stock:read"
PERM_STOCK_WRITE = "stock:write"
PERM_LANDED_COST_READ = "landed_cost:read"
PERM_LANDED_COST_WRITE = "landed_cost:write"

# Ações críticas (CURSOR_RULES §20)
PERM_RESTORE_BACKUP = "admin:restore_backup"
PERM_RUN_MIGRATION = "admin:run_migration"
PERM_CLOSE_IMPORTATION = "importation:close"
PERM_REOPEN_IMPORTATION = "importation:reopen"
PERM_CHANGE_MODAL = "logistics:change_modal"
PERM_CHANGE_EXCHANGE = "finance:change_exchange"
PERM_APPROVE_PAYMENT_WITHOUT_RECEIPT = "finance:approve_payment_without_receipt"

ALL_PERMISSIONS = [
    PERM_USERS_READ,
    PERM_USERS_WRITE,
    PERM_IMPORTATION_READ,
    PERM_IMPORTATION_WRITE,
    PERM_FINANCE_READ,
    PERM_FINANCE_WRITE,
    PERM_DOCUMENTS_READ,
    PERM_DOCUMENTS_WRITE,
    PERM_IMPORTS_READ,
    PERM_IMPORTS_WRITE,
    PERM_IMPORTS_APPROVE,
    PERM_LOGISTICS_READ,
    PERM_LOGISTICS_WRITE,
    PERM_CUSTOMS_READ,
    PERM_CUSTOMS_WRITE,
    PERM_STOCK_READ,
    PERM_STOCK_WRITE,
    PERM_LANDED_COST_READ,
    PERM_LANDED_COST_WRITE,
    PERM_RESTORE_BACKUP,
    PERM_RUN_MIGRATION,
    PERM_CLOSE_IMPORTATION,
    PERM_REOPEN_IMPORTATION,
    PERM_CHANGE_MODAL,
    PERM_CHANGE_EXCHANGE,
    PERM_APPROVE_PAYMENT_WITHOUT_RECEIPT,
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "admin": ALL_PERMISSIONS,
    "gestor": [
        PERM_USERS_READ,
        PERM_IMPORTATION_READ,
        PERM_IMPORTATION_WRITE,
        PERM_FINANCE_READ,
        PERM_FINANCE_WRITE,
        PERM_DOCUMENTS_READ,
        PERM_DOCUMENTS_WRITE,
        PERM_IMPORTS_READ,
        PERM_IMPORTS_WRITE,
        PERM_IMPORTS_APPROVE,
        PERM_LOGISTICS_READ,
        PERM_LOGISTICS_WRITE,
        PERM_CUSTOMS_READ,
        PERM_CUSTOMS_WRITE,
        PERM_STOCK_READ,
        PERM_STOCK_WRITE,
        PERM_LANDED_COST_READ,
        PERM_LANDED_COST_WRITE,
        PERM_CLOSE_IMPORTATION,
        PERM_REOPEN_IMPORTATION,
        PERM_CHANGE_MODAL,
        PERM_CHANGE_EXCHANGE,
        PERM_APPROVE_PAYMENT_WITHOUT_RECEIPT,
    ],
    "financeiro": [
        PERM_USERS_READ,
        PERM_IMPORTATION_READ,
        PERM_FINANCE_READ,
        PERM_FINANCE_WRITE,
        PERM_CHANGE_EXCHANGE,
        PERM_APPROVE_PAYMENT_WITHOUT_RECEIPT,
        PERM_CUSTOMS_READ,
        PERM_STOCK_READ,
        PERM_LANDED_COST_READ,
    ],
    "operador": [
        PERM_USERS_READ,
        PERM_IMPORTATION_READ,
        PERM_DOCUMENTS_READ,
        PERM_IMPORTS_READ,
        PERM_CUSTOMS_READ,
        PERM_STOCK_READ,
        PERM_LANDED_COST_READ,
    ],
    "comprador": [
        PERM_USERS_READ,
        PERM_IMPORTATION_READ,
        PERM_IMPORTATION_WRITE,
        PERM_DOCUMENTS_READ,
        PERM_DOCUMENTS_WRITE,
        PERM_IMPORTS_READ,
        PERM_IMPORTS_WRITE,
    ],
    "logistica": [
        PERM_USERS_READ,
        PERM_IMPORTATION_READ,
        PERM_LOGISTICS_READ,
        PERM_LOGISTICS_WRITE,
        PERM_CHANGE_MODAL,
        PERM_DOCUMENTS_READ,
        PERM_CUSTOMS_READ,
        PERM_CUSTOMS_WRITE,
        PERM_STOCK_READ,
        PERM_STOCK_WRITE,
    ],
}


def role_has_permission(role_permissions: list[str], permission: str) -> bool:
    return permission in role_permissions
