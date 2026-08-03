# J#5 — Relatório de execução (I5-6 fechamento)

| Campo | Valor |
|---|---|
| Fase | Aduana + Inventory (J#5) |
| Checkpoint | **I5-6 DONE** |
| Data | 2026-08-03 |
| Roadmap | **0.5.62** |
| Blueprint | 0.2.15 (sem mudança material nesta entrega) |
| Alembic head | `015_nationalization_inventory` |
| Classificação UI | **ACCEPTED_WITH_MINOR_BACKLOG** — [`UI_ACCEPTANCE_J5.md`](UI_ACCEPTANCE_J5.md) |

## 1. Gates técnicos

| Gate | Comando / escopo | Resultado |
|---|---|---|
| pytest J#5 + arch | `test_j5_*`, `test_customs_i5_*`, `test_inventory_i5_4`, `tests/architecture/` | **PASS** — 51 |
| generate:api | `npm run generate:api` | **PASS** |
| api-drift | `npm run check:api-drift` | **PASS** |
| tsc | `npx tsc --noEmit` | **PASS** |
| build | `npm run build` | **PASS** |
| e2e:j5 | 4 specs (i5-1, i5-2, i5-5, acceptance) | **PASS** — 4 |
| e2e:inc-6 | regressão Order-to-Pay | **PASS** — 1 |
| e2e:logistics | regressão J#4 | **PASS** — 4 |

Logs: [`logs/i5-6-pytest.txt`](logs/i5-6-pytest.txt), [`logs/i5-6-e2e-j5.txt`](logs/i5-6-e2e-j5.txt), [`logs/i5-6-e2e-inc6.txt`](logs/i5-6-e2e-inc6.txt), [`logs/i5-6-e2e-logistics.txt`](logs/i5-6-e2e-logistics.txt), [`logs/i5-6-frontend-gates.txt`](logs/i5-6-frontend-gates.txt).

## 2. Migrations 011–015 (fechadas)

| Rev | Conteúdo | Checkpoint |
|---|---|---|
| **011** | ImportProcess + joins invoice/shipment + alocações | I5-1 |
| **012** | Doganale versionada + divergências | I5-2 |
| **013** | Payee + FundingRequest + bases/tax/expense | I5-3A |
| **014** | Payable Customs + FundingPayableLink | I5-3B |
| **015** | Nationalization + Inventory + SkuPosition | I5-4 |

Head permanece **015**. I5-5/I5-6 sem migration nova.

## 3. Checkpoints I5-0…I5-6

| ID | Status |
|---|---|
| I5-0 | **DONE** |
| I5-1 | **DONE** |
| I5-2 | **DONE** |
| I5-3A | **DONE** |
| I5-3B | **DONE** |
| I5-4 | **DONE** |
| I5-5 | **DONE** |
| I5-6 | **DONE** |

## 4. Decisões (resumo)

| ID / tema | Estado |
|---|---|
| DEC-DUIMP-MULTI-SHIP | Fechada — process 1:N shipment + UNIQUE + item alloc |
| Nationalization ownership | Customs; Inventory lê via `customs.public` |
| SkuPosition | Query composta; `future_order_qty` null deferred |
| ARRIVED | Não cria stock |
| Payee | Sem FK Supplier |
| confirm Funding → Payable | I5-3B; Treasury allocation Customs ainda bloqueada (gap intencional) |
| L-007 DI vs DUIMP | Aberta — DI documental opcional |

## 5. SC-07 / SC-09 / SC-10

| SC | Critério Blueprint §15 | Evidência |
|---|---|---|
| **SC-07** | 1 DUIMP → N invoices (+ Numerário) | `j5-02`, `j5-08`…`j5-10`; pytest i5-1/i5-3* |
| **SC-09** | Nacionalização parcial | `j5-12`; `test_partial_nat_and_receipt_sc09` |
| **SC-10** | Entrada/consumo entreposto / saldo derivado | `j5-11`, `j5-13`, `j5-14`; pytest i5-4 |

## 6. Matriz requisito → teste → screenshot

| Requisito | Teste | Screenshot |
|---|---|---|
| Lista SCR-019 | e2e j5-acceptance + i5-5 | j5-01 |
| Multi invoice/shipment | e2e acceptance + i5-1; pytest i5-1 | j5-02 |
| Alocação parcial | e2e acceptance | j5-03 |
| Submit lifecycle | e2e acceptance + i5-1 | j5-04 |
| Doganale v1/v2/hist/div | e2e acceptance + i5-2; pytest i5-2 | j5-05…07 |
| Numerário + payee | e2e acceptance; pytest i5-3a | j5-08…09 |
| Payable AP Customs | e2e acceptance; pytest i5-3b | j5-10 |
| Bonded receipt | e2e acceptance; pytest i5-4 | j5-11 |
| Partial nat SC-09 | e2e acceptance; pytest i5-4 | j5-12 |
| SkuPosition SC-10 | e2e acceptance; pytest i5-4 | j5-13 |
| Movements ledger | e2e acceptance | j5-14 |
| Docs + Audit | e2e acceptance | j5-15 |
| Roles aduana/estoque | pytest i5-5 | — (smoke i5-5) |

## 7. Gaps / minor backlog

Ver [`UI_ACCEPTANCE_J5.md`](UI_ACCEPTANCE_J5.md) § Minor backlog. Nenhum BLOCKER/MAJOR aberto.

## 8. Handoff J#3 (Ingestão)

- **Pré-requisito cumprido:** Customs + Inventory (J#5) **DONE**.
- J#3 consome APIs **públicas** dos owners (customs/inventory/orders/billing/logistics); sem import de internals; sem parser nesta fase J#5.
- Foothold existente: `v2/app/ingestion/parse_it` (goldens) — **sem** pipeline.
- Objetos alvo Blueprint §§5.9, 7.2, 10: Ordine/Fattura/Packing/Doganale/Numerário/XLSX/PrintDeclaration.
- **Não iniciar J#3 nesta entrega** — próxima ação Roadmap = **planejar J#3**.

## 9. Handoff J#6 (Costing / Reconciliation)

- Depende de Aduana **DONE** (agora) + dados de Numerário/Expense.
- L-001 (tolerância logística) permanece provisória até Reconciliation.
- Landed cost / pares — fora de J#5; não iniciar J#6 agora.

## 10. Artefatos de código I5-6

| Artefato | Path |
|---|---|
| Acceptance E2E | `v2/frontend/e2e/j5-acceptance.spec.ts` |
| Suite manifest | `v2/frontend/e2e/suites/j5.txt` |
| npm script | `"e2e:j5": "node scripts/e2e-suite.mjs j5"` |
| Fix strict Submetido | `e2e/i5-1-customs.spec.ts` (status-badge) |
