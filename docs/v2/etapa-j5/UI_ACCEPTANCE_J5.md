# UI Acceptance — J#5 (I5-6)

| Campo | Valor |
|---|---|
| Data | 2026-08-03 |
| Viewport | 1366 × 900 |
| Suite | `npm run e2e:j5` → `e2e/j5-acceptance.spec.ts` |
| Classificação | **ACCEPTED_WITH_MINOR_BACKLOG** |
| SC cobertos | SC-07, SC-09, SC-10 |

## Object codes

| Código | Objeto |
|---|---|
| SCR-019 | Lista Processos Aduaneiros |
| SCR-022 | Detalhe ImportProcess (vínculos, Doganale, Numerário, Liberações, Recebimentos, Docs, Audit) |
| SCR-008 | Contas a pagar (AP) — Payable origem CUSTOMS_FUNDING |
| SCR-024 | Posição SKU (buckets) |
| SCR-025 | Movimentos de estoque |

## Matriz de screenshots

| Screenshot | Jornada | Estado | Requisitos | Resultado |
|---|---|---|---|---|
| `j5-01-process-list.png` | SCR-019 listagem | ≥1 processo com DUIMP | lista + KPI shell | **PASS** |
| `j5-02-process-links.png` | SCR-022 vínculos | 2 invoices + 2 shipments linked | DEC-DUIMP-MULTI-SHIP / SC-07 | **PASS** |
| `j5-03-item-allocations.png` | Alocações parciais | inv qty=4 / shp qty=3 | residual parcial | **PASS** |
| `j5-04-process-submitted.png` | Submit | status SUBMITTED | lifecycle DRAFT→SUBMITTED | **PASS** |
| `j5-05-doganale-v1.png` | Doganale | v1 ACTIVE com linhas | versionamento | **PASS** |
| `j5-06-doganale-v2-history.png` | Doganale supersede | v2 current + v1 SUPERSEDED | histórico | **PASS** |
| `j5-07-doganale-divergence.png` | Divergência | mensagem visível | rastreio | **PASS** |
| `j5-08-funding-request.png` | Numerário | payee Bechtrans-like + header | fixture Numerário / SC-07 | **PASS** |
| `j5-09-funding-composition.png` | Composição | bases/tax/expense; totais | structured = declared | **PASS** |
| `j5-10-customs-payable-ap.png` | AP | Payable CUSTOMS_FUNDING + payee | I5-3B denormalização | **PASS** |
| `j5-11-bonded-receipt.png` | Recebimento | BONDED_IN Confirmado | SC-10 bonded pré-nac | **PASS** |
| `j5-12-partial-nationalization.png` | Liberação | Confirmada qty parcial | SC-09 | **PASS** |
| `j5-13-sku-position.png` | SCR-024 | buckets bonded ≠ 0 | SC-10 / ADR-07 | **PASS** |
| `j5-14-inventory-movements.png` | SCR-025 | ledger com movimento | append-only | **PASS** |
| `j5-15-documents-audit.png` | Docs + Audit | PDF anexado + tabela audit | Documents/Audit | **PASS** |

Paths: `docs/v2/etapa-j5/screenshots/`.

## Minor backlog (não bloqueia aceite)

| ID | Item | Destino |
|---|---|---|
| MB-J5-1 | Link Numerário → AP usa `/ap` (rota canônica = `/payables`) | UI polish |
| MB-J5-2 | Sem usuário seed dedicado `aduana`/`estoque` (roles existem) | Identity sob demanda |
| MB-J5-3 | Payment/Allocation para Payable Customs ainda bloqueado | decisão futura / Treasury |
| MB-J5-4 | `in_transit_qty` aproximado; `future_order_qty` deferred | Reporting / Logistics |
| MB-J5-5 | Lifecycle Funding ISSUED/PARTIALLY_SETTLED/SETTLED | aberto (Blueprint) |

## Veredito

**ACCEPTED_WITH_MINOR_BACKLOG** — jornadas SC-07/09/10 demonstradas em E2E com screenshots persistidos; gaps acima são conhecidos e não impedem fechamento J#5.
