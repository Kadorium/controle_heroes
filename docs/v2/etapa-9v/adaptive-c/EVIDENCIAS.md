# Fechamento — Onda C filas adaptativas

**STATUS:** DONE técnico  
**SCR-008:** APPROVED_FOR_PROGRESSION  
**Onda C:** DONE técnico  
**Etapa 9/9V:** PARTIAL · visual PENDING_EXTERNAL_REVIEW · Onda D TODO · Inc-6 TODO

## Hipóteses

| ID | Veredito |
|---|---|
| H-C1 A0/A1 + OT columns | CONFIRMADA |
| H-C2 003/006/010 usavam children | CONFIRMADA |
| H-C3 Sem backend | CONFIRMADA |
| H-C4 Política vs tipos | CONFIRMADA (campos alinhados; payable_count null → —) |
| H-C5 Filtros/retorno/ações | CONFIRMADA |
| H-C6 children preservada | CONFIRMADA |

## Checkpoints

| CP | Fila | Gates locais | Resultado |
|---|---|---|---|
| C1 | Pedidos | unit + tsc + build | PASS |
| C2 | Faturas | unit + tsc + build | PASS |
| C3 | Pagamentos | unit (C-010) + tsc + build | PASS |
| Suite | canônico + adaptive-c | E2E 17p | PASS |

## Contratos

Confirmados no tipo FE: pedidos (`open_balance`, `commercial_total`, `invoiced_amount`, `next_due_date`, `pendencies`); faturas (`order_code`, `supplier_name`, `balance`, `net_amount`, `payable_count`); pagamentos (`supplier_name`, `amount`, `amount_*`, `external_reference`).  
Gaps: nenhum campo inventado; coluna Moeda removida em Pagamentos (MoneyDisplay).

## Legado OT `children` (após Onda C)

Consumidores restantes: `PayablesListPage`, `OrderCockpitPage`, `OrderCreatePage`, `OrderDetailPage`, `InvoiceDetailPage`, `PaymentDetailPage`, testes foundation.

Migrados para `columns`: `ApQueuePage`, `OrdersListPage`, `InvoicesListPage`, `PaymentsListPage`.

## Divergências conscientes

- `row-highlight` em Pagamentos: **não** portado (decoração visual; polish futuro).
- Pedidos: factory tipada (não constante global) por dependência de `returnTo`.
