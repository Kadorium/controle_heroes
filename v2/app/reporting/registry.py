"""Catálogo semântico J#7 — fonte única (labels PT-BR). UI não redefine fórmula."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Status = Literal["AVAILABLE", "PARTIAL", "NOT_AVAILABLE"]
DeltaPolicy = Literal["none", "prior_window"]
Section = Literal["kpi", "chart", "actions", "detail"]
Size = Literal["stat", "panel", "list", "wide"]

LAYOUT_SCHEMA_VERSION = 1
ATTENTION_LIMIT_DEFAULT = 5
PERF_FIRST_VIEWPORT_MS = 1500
PERF_SNAPSHOT_MS = 2500
SIZE_SPAN = {"stat": 3, "panel": 6, "list": 4, "wide": 12}


@dataclass(frozen=True)
class MetricDef:
    metric_id: str
    label: str
    unit_label: str
    short_description: str
    definition: str
    owner: str
    permission: str
    time_basis: str | None
    delta_policy: DeltaPolicy
    currency_policy: str
    null_policy: str
    status: Status
    limitation: str | None
    drill: str
    filters: tuple[str, ...]
    ai_ready: bool = True


@dataclass(frozen=True)
class WidgetDef:
    widget_id: str
    label: str
    short_description: str
    metric_ids: tuple[str, ...]
    permissions: tuple[str, ...]
    kind: str
    status: Status
    col: int
    span: int
    limitation: str | None = None
    section: Section = "detail"
    size: Size = "panel"
    cta_label: str | None = None
    drill: str | None = None


@dataclass(frozen=True)
class PresetDef:
    preset_id: str
    label: str
    widget_ids: tuple[str, ...]
    hidden: bool = False
    filters: tuple[str, ...] = ()


def _m(**kwargs: Any) -> MetricDef:
    return MetricDef(**kwargs)


METRICS: tuple[MetricDef, ...] = (
    _m(
        metric_id="attention.inbox",
        label="O que espera por você",
        unit_label="itens",
        short_description="Pendências dos módulos que você pode ver, ordenadas por gravidade.",
        definition="Composição de itens de ação (vencido, vence hoje, aviso). Sem pontuação opaca.",
        owner="reporting",
        permission="reporting:read",
        time_basis="due_date",
        delta_policy="none",
        currency_policy="per_item",
        null_policy="empty_states",
        status="AVAILABLE",
        limitation="Itens PARTIAL não entram. Falha de um módulo não zera os demais.",
        drill="/payables",
        filters=("date_from", "date_to", "currency", "supplier_id"),
    ),
    _m(
        metric_id="ap.open_balance_by_currency",
        label="Saldo em aberto",
        unit_label="moeda da obrigação",
        short_description="Soma dos saldos em aberto, uma barra por moeda. Não mistura euro com real.",
        definition="Σ balance de obrigações OPEN/PARTIALLY_PAID, agrupado por currency.",
        owner="billing",
        permission="billing:read",
        time_basis="due_date",
        delta_policy="prior_window",
        currency_policy="per_currency",
        null_policy="omit_currency",
        status="AVAILABLE",
        limitation=None,
        drill="/payables?pending=OPEN_BALANCE",
        filters=("date_from", "date_to", "currency", "supplier_id"),
    ),
    _m(
        metric_id="ap.overdue_by_currency",
        label="Vencido",
        unit_label="moeda da obrigação",
        short_description="Saldo e quantidade de obrigações já vencidas, por moeda.",
        definition="due_date < hoje e status aberto, agrupado por currency.",
        owner="billing",
        permission="billing:read",
        time_basis="due_date",
        delta_policy="prior_window",
        currency_policy="per_currency",
        null_policy="omit_currency",
        status="AVAILABLE",
        limitation=None,
        drill="/payables?pending=OVERDUE",
        filters=("date_from", "date_to", "currency", "supplier_id"),
    ),
    _m(
        metric_id="ap.due_today",
        label="Vence hoje",
        unit_label="moeda da obrigação",
        short_description="Saldo que vence na data de hoje, por moeda.",
        definition="due_date = hoje (servidor) e status aberto.",
        owner="billing",
        permission="billing:read",
        time_basis="due_date",
        delta_policy="none",
        currency_policy="per_currency",
        null_policy="omit_currency",
        status="AVAILABLE",
        limitation=None,
        drill="/payables",
        filters=("currency", "supplier_id"),
    ),
    _m(
        metric_id="ap.next_7d",
        label="A vencer em 7 dias",
        unit_label="moeda da obrigação",
        short_description="Saldo com vencimento nos próximos 7 dias, por moeda.",
        definition="hoje < due_date ≤ hoje+7 e status aberto.",
        owner="billing",
        permission="billing:read",
        time_basis="due_date",
        delta_policy="prior_window",
        currency_policy="per_currency",
        null_policy="omit_currency",
        status="AVAILABLE",
        limitation=None,
        drill="/payables",
        filters=("currency", "supplier_id"),
    ),
    _m(
        metric_id="ap.next_30d_by_currency",
        label="A vencer em 30 dias",
        unit_label="moeda da obrigação",
        short_description="Saldo com vencimento nos próximos 30 dias, por moeda.",
        definition="hoje < due_date ≤ hoje+30 e status aberto.",
        owner="billing",
        permission="billing:read",
        time_basis="due_date",
        delta_policy="prior_window",
        currency_policy="per_currency",
        null_policy="omit_currency",
        status="AVAILABLE",
        limitation=None,
        drill="/payables",
        filters=("currency", "supplier_id"),
    ),
    _m(
        metric_id="ap.mixed_currency",
        label="Mais de uma moeda",
        unit_label="—",
        short_description="Indica se o conjunto filtrado mistura moedas. Não some os totais.",
        definition="len(kpis_by_currency) > 1",
        owner="billing",
        permission="billing:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="flag",
        null_policy="false_if_empty",
        status="AVAILABLE",
        limitation=None,
        drill="/payables",
        filters=("currency",),
    ),
    _m(
        metric_id="ap.top_n",
        label="Maiores obrigações",
        unit_label="moeda da obrigação",
        short_description="Lista das obrigações em aberto, vencidas primeiro.",
        definition="Página da fila de contas a pagar (saldo aberto), sem misturar moedas na soma.",
        owner="billing",
        permission="billing:read",
        time_basis="due_date",
        delta_policy="none",
        currency_policy="native_row",
        null_policy="empty_table",
        status="AVAILABLE",
        limitation="Lista paginada; não é o universo completo se total > limite.",
        drill="/payables?pending=OPEN_BALANCE",
        filters=("date_from", "date_to", "currency", "supplier_id"),
    ),
    _m(
        metric_id="ap.cash_committed",
        label="Caixa comprometido",
        unit_label="moeda da obrigação",
        short_description="Quanto vence neste mês, nos dois seguintes e o que já venceu, por moeda.",
        definition="Σ balance OPEN/PARTIALLY_PAID por date_trunc mês civil (M0/M1/M2) + due < 1º dia de M0. Período não esconde vencido.",
        owner="billing",
        permission="billing:read",
        time_basis="due_date",
        delta_policy="none",
        currency_policy="per_currency",
        null_policy="empty_states",
        status="AVAILABLE",
        limitation="Não mistura moedas. Inclui vencidas mesmo com recorte futuro.",
        drill="/payables",
        filters=("date_from", "date_to", "currency", "supplier_id"),
    ),
    _m(
        metric_id="billing.invoices_draft_vs_issued",
        label="Faturas rascunho e emitidas",
        unit_label="faturas",
        short_description="Quantidade de faturas em rascunho versus emitidas.",
        definition="COUNT invoices GROUP BY status (DRAFT, ISSUED). Canceladas à parte.",
        owner="billing",
        permission="billing:read",
        time_basis="invoice_date",
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_count_ok",
        status="AVAILABLE",
        limitation=None,
        drill="/invoices",
        filters=(),
    ),
    _m(
        metric_id="treasury.unallocated_by_currency",
        label="Pagamentos registrados sem aplicar",
        unit_label="moeda do pagamento",
        short_description="Residual de pagamentos registrados ainda sem aplicar nas obrigações.",
        definition="REGISTERED com amount − alocado > 0, agrupado por currency e purpose. Não é relação pagamento↔obrigação.",
        owner="treasury",
        permission="treasury:read",
        time_basis="payment_date",
        delta_policy="none",
        currency_policy="per_currency",
        null_policy="omit_currency",
        status="AVAILABLE",
        limitation="Candidatos, não vínculo com uma obrigação específica.",
        drill="/payments?unallocated_only=1",
        filters=("currency", "supplier_id"),
    ),
    _m(
        metric_id="treasury.fx_quote_eur_brl",
        label="Cotação euro / real",
        unit_label="BRL por EUR",
        short_description="Última cotação de mercado euro contra real, com fonte e se está velha.",
        definition="get_latest_quote(EUR, BRL). Ausência = cotação indisponível, não zero.",
        owner="treasury",
        permission="treasury:fx_read",
        time_basis="as_of",
        delta_policy="none",
        currency_policy="named_quote",
        null_policy="unavailable",
        status="AVAILABLE",
        limitation="Par de mercado EUR/BRL.",
        drill="/payables",
        filters=("as_of",),
    ),
    _m(
        metric_id="treasury.fx_exposure",
        label="Exposição em euro",
        unit_label="BRL equivalente (nomeado)",
        short_description="Saldo em euro em aberto, equivalente em real e o efeito de o euro variar 1%.",
        definition="open_balance EUR × get_latest_quote(EUR,BRL). Choque ±1% = notional × taxa × 0,01. USD sem par = recusa de equivalente, não zero.",
        owner="reporting",
        permission="treasury:fx_read",
        time_basis="as_of",
        delta_policy="none",
        currency_policy="named_quote",
        null_policy="unavailable",
        status="AVAILABLE",
        limitation="Não é câmbio realizado. Par EUR/BRL.",
        drill="/payables",
        filters=("as_of", "currency"),
    ),
    _m(
        metric_id="orders.count_by_status",
        label="Pedidos por situação",
        unit_label="pedidos",
        short_description="Quantidade de pedidos em cada situação (rascunho, confirmado, cancelado).",
        definition="COUNT orders GROUP BY status.",
        owner="orders",
        permission="orders:read",
        time_basis="order_date",
        delta_policy="prior_window",
        currency_policy="none",
        null_policy="zero_count_ok",
        status="AVAILABLE",
        limitation=None,
        drill="/orders",
        filters=("date_from", "date_to"),
    ),
    _m(
        metric_id="orders.unpriced_or_unbound_commitment",
        label="Pedidos com pendência de cadastro",
        unit_label="linhas",
        short_description="Linhas sem preço ou compromisso ainda sem produto.",
        definition="OrderItem.unit_price IS NULL ou line_kind=COMMITMENT em pedidos não cancelados.",
        owner="orders",
        permission="orders:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_count_ok",
        status="AVAILABLE",
        limitation=None,
        drill="/orders",
        filters=(),
    ),
    _m(
        metric_id="orders.qty_to_invoice_residual",
        label="Quantidade a faturar",
        unit_label="quantidade",
        short_description="Soma da quantidade pedida ainda não faturada em pedidos confirmados.",
        definition="Σ (qty pedido − qty emitida) em pedidos CONFIRMED.",
        owner="billing",
        permission="billing:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_qty_ok",
        status="AVAILABLE",
        limitation="Não é valor em dinheiro.",
        drill="/orders",
        filters=(),
    ),
    _m(
        metric_id="orders.billing_progress",
        label="Pedidos e faturamento",
        unit_label="moeda do pedido",
        short_description="Quanto já foi confirmado, faturado e ainda falta faturar, por moeda.",
        definition="Σ linhas CONFIRMED com preço; Σ payables de faturas ISSUED; residual = confirmado − faturado (não negativo).",
        owner="billing",
        permission="billing:read",
        time_basis="order_date",
        delta_policy="none",
        currency_policy="per_currency",
        null_policy="empty_states",
        status="AVAILABLE",
        limitation="Marcos do cronograma ficam no pedido, não neste bloco.",
        drill="/orders",
        filters=("currency",),
    ),
    _m(
        metric_id="goods.flow",
        label="Mercadoria em movimento",
        unit_label="contagens independentes",
        short_description="Pedidos confirmados, linhas a faturar, embarques em curso, aduana e estoque — cada um no seu conjunto.",
        definition="Composição de contagens dos donos. Proibido tratar como funil ou o mesmo conjunto de peças.",
        owner="reporting",
        permission="reporting:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="omit_segment",
        status="AVAILABLE",
        limitation="Não é o mesmo conjunto de peças. Segmento omitido sem *:read do dono.",
        drill="/shipments",
        filters=(),
    ),
    _m(
        metric_id="logistics.shipments_by_status",
        label="Embarques por situação",
        unit_label="embarques",
        short_description="Quantidade de embarques planejados, reservados, em trânsito e chegados.",
        definition="COUNT shipments GROUP BY status.",
        owner="logistics",
        permission="logistics:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_count_ok",
        status="AVAILABLE",
        limitation="Atraso versus data prevista não é fato desta métrica.",
        drill="/shipments",
        filters=(),
    ),
    _m(
        metric_id="customs.processes_by_status",
        label="Processos de importação",
        unit_label="processos",
        short_description="Quantidade de processos por situação. Zero processos é ausência conhecida, não erro.",
        definition="COUNT import_processes GROUP BY status (exceto cancelados no total operacional).",
        owner="customs",
        permission="customs:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="known_absence",
        status="AVAILABLE",
        limitation="Copy de ausência quando total operacional = 0.",
        drill="/customs",
        filters=(),
    ),
    _m(
        metric_id="inventory.qty_by_location_type",
        label="Saldos por regime",
        unit_label="quantidade",
        short_description="Quantidade em entreposto, doméstico e quarentena. Não é valor em dinheiro.",
        definition="Σ qty de stock_balances com qty>0 agrupado por location_type.",
        owner="inventory",
        permission="inventory:read",
        time_basis="as_of",
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_qty_ok",
        status="AVAILABLE",
        limitation="Sem valor de estoque. Trânsito por SKU não entra (não é fato).",
        drill="/inventory/movements",
        filters=("as_of",),
    ),
    _m(
        metric_id="catalog.products_total",
        label="Produtos no cadastro",
        unit_label="produtos",
        short_description="Total de produtos no cadastro, inclusive histórico importado.",
        definition="product_list_summary.total — universo completo (todos os source_kind).",
        owner="catalog",
        permission="catalog:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_count_ok",
        status="AVAILABLE",
        limitation="Universo completo, inclusive source_kind=heroes_csv.",
        drill="/catalog/products",
        filters=(),
    ),
    _m(
        metric_id="catalog.needs_review",
        label="Produtos para revisar",
        unit_label="produtos",
        short_description="Produtos marcados para revisão comercial.",
        definition="import_decision = REVISAR.",
        owner="catalog",
        permission="catalog:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_count_ok",
        status="AVAILABLE",
        limitation="Universo completo do summary.",
        drill="/catalog/products?needs_review=1",
        filters=(),
    ),
    _m(
        metric_id="catalog.classification_review",
        label="Classificação a revisar",
        unit_label="produtos",
        short_description="Produtos com classificação em revisão.",
        definition="taxonomy_status = REVIEW.",
        owner="catalog",
        permission="catalog:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_count_ok",
        status="AVAILABLE",
        limitation=None,
        drill="/catalog/products?needs_classification_review=1",
        filters=(),
    ),
    _m(
        metric_id="catalog.missing_ncm",
        label="Sem NCM",
        unit_label="produtos",
        short_description="Produtos sem NCM no cadastro.",
        definition="ncm IS NULL.",
        owner="catalog",
        permission="catalog:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_count_ok",
        status="AVAILABLE",
        limitation="Não usar missing_image (placeholder igual ao total).",
        drill="/catalog/products",
        filters=(),
    ),
    _m(
        metric_id="costing.operational_published",
        label="Custo operacional publicado",
        unit_label="BRL",
        short_description="Há versão publicada de custo desembarcado? Sem versão = ausência, não R$ 0.",
        definition="COUNT costing_cases com current_published_id. Total BRL só se published>0.",
        owner="costing",
        permission="costing:read",
        time_basis="as_of",
        delta_policy="none",
        currency_policy="brl",
        null_policy="known_absence",
        status="AVAILABLE",
        limitation="Não é P&L nem custo de uma compra real (Elo 9).",
        drill="/costing",
        filters=("as_of",),
    ),
    _m(
        metric_id="costing.draft_or_blocked_cases",
        label="Custos em rascunho",
        unit_label="versões",
        short_description="Versões em rascunho e rascunhos com cobertura incompleta.",
        definition="COUNT costing_versions DRAFT; subset partial_coverage.",
        owner="costing",
        permission="costing:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_count_ok",
        status="AVAILABLE",
        limitation=None,
        drill="/costing",
        filters=(),
    ),
    _m(
        metric_id="ingestion.queue_age_by_family",
        label="Documentos em revisão",
        unit_label="documentos",
        short_description="Quantidade na fila de ingestão por tipo, com o mais antigo.",
        definition="COUNT ingestion_documents (não READY/REJECTED) GROUP BY doc_type + MIN(updated_at).",
        owner="ingestion",
        permission="ingestion:read",
        time_basis=None,
        delta_policy="none",
        currency_policy="none",
        null_policy="zero_count_ok",
        status="AVAILABLE",
        limitation=None,
        drill="/ingestion",
        filters=(),
    ),
    _m(
        metric_id="import.situation",
        label="Fluxo da importação",
        unit_label="processos",
        short_description="Processos de importação em andamento. Zero é ausência, não R$ 0.",
        definition="COUNT processos operacionais (não cancelados). Custo e estoque vivem em widgets próprios.",
        owner="reporting",
        permission="reporting:read",
        time_basis="as_of",
        delta_policy="none",
        currency_policy="none",
        null_policy="known_absence",
        status="AVAILABLE",
        limitation="Só processos. Sem permissão customs:read o bloco some.",
        drill="/customs",
        filters=("as_of",),
    ),
    _m(
        metric_id="treasury.fx_series",
        label="Tendência euro / real",
        unit_label="taxa",
        short_description="Cotações de mercado EUR/BRL dos últimos 30 dias. Sem interpolar dias vazios.",
        definition="Última cotação observada por dia em fx_market_quotes no recorte.",
        owner="treasury",
        permission="treasury:fx_read",
        time_basis="as_of",
        delta_policy="none",
        currency_policy="pair",
        null_policy="known_absence",
        status="AVAILABLE",
        limitation="Só dias com cotação real. Não é câmbio realizado.",
        drill="",
        filters=("as_of",),
    ),
    _m(
        metric_id="catalog.commercial_availability",
        label="Disponível para oferecer",
        unit_label="quantidade",
        short_description="Estoque por produto, o que está chegando e o que pede atenção. Sem demanda.",
        definition="Posição por regime + residual de desembaraço + embarque em trânsito, paginado.",
        owner="reporting",
        permission="catalog:read",
        time_basis="as_of",
        delta_policy="none",
        currency_policy="none",
        null_policy="dash_without_fact",
        status="AVAILABLE",
        limitation="Entrada prevista só aparece com fato (trânsito ou desembaraço). Nunca 0 inventado.",
        drill="/catalog/products",
        filters=("q", "category", "product_type", "status"),
    ),
    _m(
        metric_id="control.exceptions",
        label="Exceções acionáveis",
        unit_label="itens",
        short_description="Pendências de toda a operação, por gravidade e módulo.",
        definition="Merge de exceptions() dos donos (billing, catalog, ingestion, customs, costing, treasury, orders).",
        owner="reporting",
        permission="reporting:read",
        time_basis="as_of",
        delta_policy="none",
        currency_policy="per_item",
        null_policy="empty_states",
        status="AVAILABLE",
        limitation="Falha de um módulo não zera os demais. Falha de ingestão ≠ aguardando revisão.",
        drill="/payables",
        filters=("severity", "module"),
    ),
)

# Widgets selecionáveis. NOT_AVAILABLE não entra aqui.
WIDGETS: tuple[WidgetDef, ...] = (
    WidgetDef(
        "attention.inbox",
        "O que espera por você",
        "Pendências ordenadas por gravidade.",
        ("attention.inbox",),
        ("reporting:read",),
        "inbox",
        "AVAILABLE",
        1,
        12,
        None,
        "actions",
        "wide",
        "Ver decisões",
        "/payables",
    ),
    WidgetDef(
        "ap.cash_committed",
        "Caixa nos próximos meses",
        "Vencimentos do mês, dos dois seguintes e o já vencido, por moeda.",
        ("ap.cash_committed", "ap.mixed_currency"),
        ("billing:read",),
        "cash_months",
        "AVAILABLE",
        1,
        6,
        None,
        "chart",
        "panel",
        "Ver a pagar",
        "/payables",
    ),
    WidgetDef(
        "ap.next_7d",
        "A vencer em 7 dias",
        "Saldo a vencer em 7 dias, por moeda.",
        ("ap.next_7d", "ap.mixed_currency"),
        ("billing:read",),
        "kpi_currency",
        "AVAILABLE",
        5,
        4,
    ),
    WidgetDef(
        "ap.overdue",
        "Vencido",
        "Saldo já vencido, por moeda.",
        ("ap.overdue_by_currency",),
        ("billing:read",),
        "kpi_currency",
        "AVAILABLE",
        1,
        3,
        None,
        "kpi",
        "stat",
        "Ver vencidas",
        "/payables?pending=OVERDUE",
    ),
    WidgetDef(
        "ap.open_balance",
        "Saldo em aberto",
        "Saldo em aberto, por moeda.",
        ("ap.open_balance_by_currency",),
        ("billing:read",),
        "kpi_currency",
        "AVAILABLE",
        1,
        4,
    ),
    WidgetDef(
        "ap.aging_bar",
        "Vencimentos por prazo",
        "Proporção vencido / hoje / 7 dias / restante, por moeda.",
        ("ap.overdue_by_currency", "ap.due_today", "ap.next_7d", "ap.open_balance_by_currency"),
        ("billing:read",),
        "aging_bar",
        "AVAILABLE",
        1,
        6,
    ),
    WidgetDef(
        "ap.top_n",
        "Maiores obrigações",
        "Obrigações em aberto, vencidas primeiro.",
        ("ap.top_n",),
        ("billing:read",),
        "table",
        "AVAILABLE",
        1,
        6,
    ),
    WidgetDef(
        "catalog.quality",
        "Qualidade do cadastro",
        "Totais de revisão, classificação e NCM.",
        (
            "catalog.products_total",
            "catalog.needs_review",
            "catalog.classification_review",
            "catalog.missing_ncm",
        ),
        ("catalog:read",),
        "catalog_quality",
        "AVAILABLE",
        9,
        4,
        "Universo: catálogo completo, inclusive histórico importado.",
    ),
    WidgetDef(
        "treasury.fx_exposure",
        "Exposição em euro",
        "Saldo em euro, equivalente em real e choque de 1%.",
        ("treasury.fx_exposure",),
        ("billing:read", "treasury:fx_read"),
        "fx_exposure",
        "AVAILABLE",
        6,
        3,
        "Não é câmbio realizado. Par EUR/BRL.",
        "kpi",
        "stat",
        "Ver a pagar",
        None,
    ),
    WidgetDef(
        "treasury.fx_quote",
        "Cotação euro / real",
        "Última cotação de mercado, com fonte.",
        ("treasury.fx_quote_eur_brl",),
        ("treasury:fx_read",),
        "quote",
        "AVAILABLE",
        7,
        3,
    ),
    WidgetDef(
        "treasury.unallocated",
        "Pagamentos registrados sem aplicar",
        "Residual registrado ainda sem aplicar.",
        ("treasury.unallocated_by_currency",),
        ("treasury:read",),
        "kpi_currency",
        "AVAILABLE",
        7,
        4,
        "Não é vínculo pagamento↔obrigação.",
    ),
    WidgetDef(
        "import.situation",
        "Fluxo da importação",
        "Processos de importação em andamento.",
        ("customs.processes_by_status",),
        ("reporting:read",),
        "absence_block",
        "AVAILABLE",
        9,
        4,
    ),
    WidgetDef(
        "costing.operational_published",
        "Custo publicado",
        "Há versão publicada de custo desembarcado.",
        ("costing.operational_published",),
        ("costing:read",),
        "absence_block",
        "AVAILABLE",
        1,
        4,
        "Não é P&L nem custo de uma compra real.",
    ),
    WidgetDef(
        "goods.flow",
        "Mercadoria em movimento",
        "Contagens independentes no caminho da mercadoria.",
        ("goods.flow",),
        ("reporting:read",),
        "goods_flow",
        "AVAILABLE",
        9,
        6,
        "Contagens independentes; o mesmo item pode aparecer em mais de uma.",
        "detail",
        "panel",
        "Ver embarques",
        "/shipments",
    ),
    WidgetDef(
        "orders.billing_progress",
        "Pedidos e faturamento",
        "Confirmado, faturado e a faturar, por moeda.",
        ("orders.billing_progress",),
        ("orders:read", "billing:read"),
        "billing_progress",
        "AVAILABLE",
        6,
        6,
        "Marcos do cronograma ficam no pedido, não neste bloco.",
        "detail",
        "panel",
        "Ver pedidos",
        "/orders",
    ),
    WidgetDef(
        "orders.status",
        "Pedidos por situação",
        "Contagem de pedidos por situação.",
        ("orders.count_by_status", "orders.unpriced_or_unbound_commitment"),
        ("orders:read",),
        "counts",
        "AVAILABLE",
        1,
        4,
    ),
    WidgetDef(
        "logistics.shipments",
        "Embarques",
        "Embarques por situação.",
        ("logistics.shipments_by_status",),
        ("logistics:read",),
        "counts",
        "AVAILABLE",
        1,
        4,
    ),
    WidgetDef(
        "inventory.overview",
        "Saldos por regime",
        "Quantidade em entreposto, doméstico e quarentena.",
        ("inventory.qty_by_location_type",),
        ("inventory:read",),
        "counts",
        "AVAILABLE",
        5,
        4,
    ),
    WidgetDef(
        "ingestion.queue",
        "Documentos em revisão",
        "Fila de ingestão por tipo.",
        ("ingestion.queue_age_by_family",),
        ("ingestion:read",),
        "counts",
        "AVAILABLE",
        10,
        3,
    ),
    WidgetDef(
        "billing.invoices_split",
        "Faturas rascunho e emitidas",
        "Contagem DRAFT versus ISSUED.",
        ("billing.invoices_draft_vs_issued",),
        ("billing:read",),
        "counts",
        "AVAILABLE",
        1,
        4,
    ),
    WidgetDef(
        "orders.qty_residual",
        "Quantidade a faturar",
        "Quantidade pedida ainda não faturada.",
        ("orders.qty_to_invoice_residual",),
        ("billing:read",),
        "kpi_plain",
        "AVAILABLE",
        1,
        4,
    ),
    WidgetDef(
        "ap.cash_due",
        "A vencer",
        "Saldo com vencimento neste mês e nos dois seguintes.",
        ("ap.cash_committed",),
        ("billing:read",),
        "kpi_currency",
        "AVAILABLE",
        4,
        3,
        None,
        "kpi",
        "stat",
        "Ver a pagar",
        "/payables",
    ),
    WidgetDef(
        "orders.to_invoice",
        "A faturar",
        "Valor confirmado ainda não faturado, por moeda.",
        ("orders.billing_progress",),
        ("orders:read", "billing:read"),
        "kpi_currency",
        "AVAILABLE",
        10,
        3,
        None,
        "kpi",
        "stat",
        "Ver pedidos",
        "/orders",
    ),
    WidgetDef(
        "treasury.fx_trend",
        "Euro / real — 30 dias",
        "Tendência da cotação de mercado. Só dias com fato.",
        ("treasury.fx_series",),
        ("treasury:fx_read",),
        "fx_trend",
        "AVAILABLE",
        7,
        6,
        "Não interpola dias sem cotação.",
        "chart",
        "panel",
        "Ver câmbio",
        None,
    ),
    WidgetDef(
        "commercial.availability",
        "Disponível para oferecer",
        "O que há em estoque, o que está chegando e o que pede atenção.",
        ("catalog.commercial_availability",),
        ("catalog:read", "inventory:read"),
        "commercial",
        "AVAILABLE",
        1,
        12,
        "Entrada prevista só com fato. Sem métrica de demanda.",
        "detail",
        "wide",
        "Ver catálogo",
        "/catalog/products",
    ),
    WidgetDef(
        "control.exceptions",
        "Exceções acionáveis",
        "O que bloqueia ou atrasa a operação, por gravidade e módulo.",
        ("control.exceptions",),
        ("reporting:read",),
        "exceptions",
        "AVAILABLE",
        1,
        12,
        "Falha de um módulo não zera os demais.",
        "detail",
        "wide",
        None,
        None,
    ),
)

PRESETS: tuple[PresetDef, ...] = (
    PresetDef(
        "executiva",
        "Executiva",
        (
            "ap.overdue",
            "ap.cash_due",
            "treasury.fx_exposure",
            "orders.to_invoice",
            "ap.cash_committed",
            "treasury.fx_trend",
            "attention.inbox",
            "orders.billing_progress",
            "goods.flow",
        ),
        False,
        ("period", "currency"),
    ),
    PresetDef(
        "comercial",
        "Comercial",
        ("commercial.availability",),
        False,
        ("q", "category", "product_type", "status"),
    ),
    PresetDef(
        "controle",
        "Controle",
        ("control.exceptions",),
        False,
        ("severity", "module"),
    ),
    PresetDef(
        "financeiro",
        "Financeiro",
        (
            "attention.inbox",
            "ap.overdue",
            "ap.next_7d",
            "ap.open_balance",
            "ap.aging_bar",
            "ap.top_n",
            "treasury.fx_quote",
            "treasury.unallocated",
        ),
        True,
        ("period", "currency", "supplier_id"),
    ),
    PresetDef(
        "compras",
        "Compras",
        (
            "attention.inbox",
            "orders.billing_progress",
            "catalog.quality",
            "orders.status",
            "orders.qty_residual",
            "billing.invoices_split",
        ),
        True,
        ("period",),
    ),
    PresetDef(
        "operacao",
        "Operação",
        (
            "attention.inbox",
            "logistics.shipments",
            "ingestion.queue",
        ),
        True,
        ("period",),
    ),
    PresetDef(
        "aduana",
        "Aduana",
        ("import.situation", "attention.inbox"),
        True,
        ("period",),
    ),
    PresetDef(
        "estoque",
        "Estoque",
        ("inventory.overview", "import.situation"),
        True,
        ("period",),
    ),
    PresetDef(
        "produtos",
        "Produtos",
        ("catalog.quality",),
        True,
        ("q", "category"),
    ),
    PresetDef(
        "custos",
        "Custos",
        ("costing.operational_published",),
        True,
        (),
    ),
)

ROLE_DEFAULT_PRESET = {
    "admin": "executiva",
    "comprador": "comercial",
    "aduana": "controle",
    "estoque": "controle",
}

ROLE_FALLBACK_PATH = {
    "admin": "/dashboard",
    "comprador": "/dashboard",
    "aduana": "/customs",
    "estoque": "/inventory/movements",
}


def metrics_by_id() -> dict[str, MetricDef]:
    return {m.metric_id: m for m in METRICS}


def widgets_by_id() -> dict[str, WidgetDef]:
    return {w.widget_id: w for w in WIDGETS}


def presets_by_id() -> dict[str, PresetDef]:
    return {p.preset_id: p for p in PRESETS}


def selectable_widget_ids() -> frozenset[str]:
    return frozenset(w.widget_id for w in WIDGETS if w.status != "NOT_AVAILABLE")


def default_layout(preset_id: str) -> dict[str, Any]:
    preset = presets_by_id()[preset_id]
    wmap = widgets_by_id()
    slots = []
    for wid in preset.widget_ids:
        w = wmap[wid]
        span = SIZE_SPAN.get(w.size, w.span)
        slots.append({"widget_id": wid, "col": w.col, "span": span, "size": w.size, "section": w.section})
    return {"schema_version": LAYOUT_SCHEMA_VERSION, "slots": slots}


def metric_to_public(m: MetricDef) -> dict[str, Any]:
    d = asdict(m)
    d["filters"] = list(m.filters)
    return d


def widget_to_public(w: WidgetDef) -> dict[str, Any]:
    return {
        "widget_id": w.widget_id,
        "label": w.label,
        "short_description": w.short_description,
        "metric_ids": list(w.metric_ids),
        "permissions": list(w.permissions),
        "kind": w.kind,
        "status": w.status,
        "limitation": w.limitation,
        "col": w.col,
        "span": SIZE_SPAN.get(w.size, w.span),
        "section": w.section,
        "size": w.size,
        "cta_label": w.cta_label,
        "drill": w.drill,
    }


def render_catalog_markdown() -> str:
    lines = [
        "# Catálogo de métricas J#7",
        "",
        "Gerado a partir de `app.reporting.registry`. Não editar à mão.",
        "",
        f"LAYOUT_SCHEMA_VERSION = {LAYOUT_SCHEMA_VERSION}",
        f"ATTENTION_LIMIT_DEFAULT = {ATTENTION_LIMIT_DEFAULT}",
        "",
        "## Métricas",
        "",
        "| metric_id | label | owner | status | time_basis | delta_policy | permission |",
        "|---|---|---|---|---|---|---|",
    ]
    for m in METRICS:
        lines.append(
            f"| `{m.metric_id}` | {m.label} | {m.owner} | {m.status} | {m.time_basis or '—'} | {m.delta_policy} | `{m.permission}` |"
        )
    lines += ["", "## Widgets", "", "| widget_id | label | status | kind |", "|---|---|---|---|"]
    for w in WIDGETS:
        lines.append(f"| `{w.widget_id}` | {w.label} | {w.status} | {w.kind} |")
    lines += ["", "## Presets", ""]
    for p in PRESETS:
        lines.append(f"- **{p.label}** (`{p.preset_id}`): " + ", ".join(f"`{x}`" for x in p.widget_ids))
    lines.append("")
    return "\n".join(lines)


def validate_registry() -> None:
    ids = [m.metric_id for m in METRICS]
    assert len(ids) == len(set(ids)), "metric_id duplicado"
    for m in METRICS:
        assert m.label.strip(), m.metric_id
        assert m.unit_label.strip(), m.metric_id
        assert m.short_description.strip(), m.metric_id
        assert "Fila AP" not in m.label and "Fila FX" not in m.label, m.metric_id
        if m.time_basis in (None, "as_of"):
            assert m.delta_policy == "none", m.metric_id
        if m.delta_policy == "prior_window":
            assert m.time_basis in {
                "due_date",
                "order_date",
                "payment_date",
                "invoice_date",
            }, m.metric_id
        assert m.status in ("AVAILABLE", "PARTIAL", "NOT_AVAILABLE")
    wids = [w.widget_id for w in WIDGETS]
    assert len(wids) == len(set(wids))
    mmap = metrics_by_id()
    for w in WIDGETS:
        assert w.status != "NOT_AVAILABLE"
        assert w.label.strip() and "Fila AP" not in w.label
        assert w.section in ("kpi", "chart", "actions", "detail")
        assert w.size in SIZE_SPAN
        for mid in w.metric_ids:
            assert mid in mmap, mid
            assert mmap[mid].status != "NOT_AVAILABLE", mid
    wset = set(wids)
    for p in PRESETS:
        for wid in p.widget_ids:
            assert wid in wset, f"{p.preset_id} unknown widget {wid}"


validate_registry()
