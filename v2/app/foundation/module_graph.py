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
    ".advance_commands",
    ".parse_it",
    ".divergence",
    ".doganale_commands",
    ".funding_commands",
    ".nationalization_commands",
    ".dossier_commands",
    ".reconciler",
    ".annotations",
    ".numerario_commit_commands",
    ".fattura_commit_commands",
    ".fattura_line_match",
    ".fattura_order_candidates",
    ".packing_commit_commands",
    ".packing_line_match",
    ".packing_order_candidates",
    ".doganale_commit_commands",
    ".print_commit_commands",
    ".xlsx_commit_commands",
    ".metrics_commands",
    ".metrics_models",
    ".schedule",
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
    # J4-FIN FIN-1: orders (Payment.order_id / adiantamento ACCONTO)
    "treasury": frozenset({"billing", "catalog", "documents", "audit", "orders"}),
    # Reporting: arestas validadas pelo uso real em queries.py (públicas apenas)
    "reporting": frozenset({"orders", "billing", "treasury", "catalog", "documents", "audit"}),
    # J3-I3: documents (promote), orders (DRAFT), catalog (matching)
    # J3-I4: billing (Invoice DRAFT via create_invoice, set_terms)
    # J3-I5: logistics (Shipment PLANNED via PL commit), customs (ImportProcess DRAFT via Doganale commit)
    "ingestion": frozenset({"audit", "documents", "orders", "catalog", "billing", "logistics", "customs"}),
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
        # RUX-2R-b: trilha de falha fora da UoW precisa de SessionLocal
        "commit_failure.py",
    }
)
