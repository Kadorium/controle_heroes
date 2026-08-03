"""Grafo canônico de dependências entre pacotes de módulo (Blueprint §5.16).

A --> B significa: A pode importar a API pública de B (`public`).
Foundation não é nó de domínio (composition root).
`routes.py` nos módulos pode importar foundation + audit (HTTP composition) — ver arch test.
"""

INTERNAL_SUFFIXES = (
    ".models",
    ".repository",
    ".commands",
    ".queries",
    ".errors",
    ".money",
    ".storage",
    ".seed",
    ".security",
    ".liquidation",
    ".fx_commands",
    ".fx_queries",
    ".fx_money",
    ".fx_models",
    ".fx_provider",
    ".fx_provider_http",
    ".fx_valuation",
    ".parse_it",
    ".divergence",
    ".doganale_commands",
    ".funding_commands",
    ".nationalization_commands",
)

MODULE_PACKAGES = frozenset(
    {
        "identity",
        "audit",
        "documents",
        "catalog",
        "orders",
        "billing",
        "treasury",
        "reporting",
        "ingestion",
        "logistics",
        "customs",
        "inventory",
    }
)

ALLOWED_DEPS: dict[str, frozenset[str]] = {
    "identity": frozenset(),
    "audit": frozenset(),
    "documents": frozenset(),
    "catalog": frozenset({"audit"}),
    "orders": frozenset({"catalog", "documents", "audit"}),
    "billing": frozenset({"orders", "catalog", "documents", "audit"}),
    "treasury": frozenset({"billing", "catalog", "documents", "audit"}),
    # Reporting: arestas validadas pelo uso real em queries.py (públicas apenas)
    "reporting": frozenset({"orders", "billing", "treasury", "catalog", "documents", "audit"}),
    # Inc-6 foothold: parse_it only — sem arestas J#3 (Catalog/Orders/Billing)
    "ingestion": frozenset(),
    "logistics": frozenset({"orders", "documents", "audit"}),
    # J#5: Customs ↛ Treasury; Product opcional via catalog; Inventory ↛ Orders
    "customs": frozenset({"billing", "logistics", "documents", "audit", "catalog"}),
    "inventory": frozenset({"customs", "catalog", "logistics", "documents", "audit"}),
}

# Arquivos de domínio que podem importar foundation (além de models→database)
FOUNDATION_ALLOWED_FILENAMES = frozenset(
    {
        "routes.py",
        "fx_routes.py",
        "doganale_routes.py",
        "funding_routes.py",
        "nationalization_routes.py",
    }
)
