# Grupo B — Evidências

## 1. Estado inicial
- Grupo A **DONE** (Roadmap 0.5.29)
- Enrichment parcial em WIP: Reporting `orders-list`, InvoiceListItem campos, páginas AS-IS parcialmente migradas
- `epic_v2_test` @ 5433 confirmado

## 2. Incrementos executados
- **I9-2** Pedidos TARGET + `GET /api/reporting/orders-list` (owner Reporting; perm `orders:read`); ausência financeira = `—` / null
- **I9-3** Novo pedido no DS (`PageHeader`, `OperationalTable`, `Button`, `ConfirmationModal`); preço vazio ? zero
- **I9-4** Cockpit RO com breadcrumb Compras/Pedidos; KPIs Reporting; embed comercial para escrita (não stub)
- **I9-5** Faturas lista+detalhe; `supplier_name` / `payable_count`; emissão via `ConfirmationModal` (cria Payables); ACCONTO omitido

## 3. Hipóteses
| Hipótese | Veredito |
|---|---|
| Orders importa Billing para enrich | **Refutada** (module_graph) ? enrich em Reporting |
| `invoice_net(inv)` na agregação | **Bug** ? corrigido `invoice_net(inv.items)` + `decimal_str` |
| Confirmação via `window.confirm` | **Substituída** por ConfirmationModal |

## 4. Arquivos
**Criados:** `ui/ConfirmationModal.tsx`; `e2e/i9-grupo-b.spec.ts`; pytest enrichment em `test_reporting_api.py`  
**Alterados:** `billing/queries.py`, `billing/routes.py`, `billing/public.py`, `orders/routes.py`, `reporting/{queries,routes,public}.py`, `OrdersListPage`, `OrderCreatePage`, `OrderCockpitPage`, `InvoicesListPage`, `InvoiceDetailPage`, `reportingApi.ts`, OpenAPI gerado, E2E inc1/2/3/4/5  
**Removidos:** nenhum

## 5. Contratos
- `GET /api/reporting/orders-list` (novo)
- `InvoiceListItem`: `supplier_name`, `payable_count`
- `OrderListItem` (GET /orders): `supplier_name`
- OpenAPI/schema regenerados

## 6. Testes
- Unit FE: **25 passed**
- Build/tsc: **PASS**
- Pytest enrichment: **2 passed** (`test_orders_list_enrichment_*`)
- E2E (`E2E_SPECS=i9-grupo-b,inc1-orders,inc2-billing,inc5-ap-cockpit`, `epic_v2_test`): **4 passed**
- Log: `logs/grupo-B-e2e.txt`

## 7–8. Visual
- 1366: `screenshots/i9-2-orders-1366.png`, `i9-3-new-order-1366.png`, `i9-4-cockpit-1366.png`, `i9-5-invoices-1366.png`
- 1440: `screenshots/i9-2-orders-1440.png`

## 9. Telas navegadas
Login ? Pedidos ? Novo pedido ? Cockpit ? Comercial ? Fatura (issue) ? Faturas ? Contas a pagar (inc5)

## 10–12. Regressões / correções
- `order_list_financials` quebrava com Invoice não-iterável ? items + string money
- E2E: modal confirmação + cockpit + link Pedidos ambíguo (breadcrumb)

## 13. Dívidas
- Cockpit ainda embute escrita comercial (toggle) — RO puro via deep-link separado = dívida leve
- Focus trap modal / retorno scroll = I9-9
- G02 / Payments DS = Grupo C
- ACCONTO / L-005 abertos

## 14. Decisões técnicas
| Decisão | Hipótese | Evidência | Solução | Impacto | Rollback |
|---|---|---|---|---|---|
| Enrich em Reporting | Orders?Billing | module_graph | `/reporting/orders-list` | FE usa reportingApi | Remover route+query |
| Modal em vez de dialog | window.confirm | Handoff §27.6 | ConfirmationModal | E2E selectors | Reverter onClick |

## 15. Rollback
Diff WIP nos arquivos §4; sem git revert.

## 16. Status do grupo
**DONE**

## 17. Condição para avançar
Gates B verdes ? iniciar Grupo C (sem backend).
