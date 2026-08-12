# Etapa J#5 — Customs + Inventory

| Campo | Valor |
|---|---|
| Fase | Aduana + Inventory (J#5) |
| Status | **DONE** (I5-0…I5-6 + patch fechamento C0…C5) |
| Início | 2026-08-03 |
| Fechamento | 2026-08-04 (patch C5) |
| Blueprint | **0.2.16** |
| Roadmap | **0.5.63** |
| Alembic | **`015_nationalization_inventory`** (head) |
| Aceite UI | **ACCEPTED_WITH_BACKLOG** — [`UI_ACCEPTANCE_J5.md`](UI_ACCEPTANCE_J5.md) |
| Relatório | [`J5_EXECUTION_REPORT.md`](J5_EXECUTION_REPORT.md) |
| Patch | [`patch-close/`](patch-close/) |

## Sequência de migrations J#5

| Rev | Escopo | Checkpoint |
|---|---|---|
| **011** | ImportProcess + joins + alocações item | **I5-1 DONE** |
| **012** | Doganale versionada | **I5-2 DONE** |
| **013** | FundingRequest / Payee / linhas | **I5-3A DONE** |
| **014** | Payables Customs / FundingPayableLink | **I5-3B DONE** |
| **015** | Nationalization + Inventory | **I5-4 DONE** |

Política: migrations imutáveis após merge; sem tabelas futuras vazias só para reservar número.

## Checkpoints

| ID | Escopo | Status |
|---|---|---|
| **I5-0** | Decisões + scaffold | **DONE** |
| **I5-1** | ImportProcess + vínculos + UI mínima | **DONE** |
| **I5-2** | Doganale versionada + divergências + UI | **DONE** |
| **I5-3A** | Numerário + Payee + UI | **DONE** |
| **I5-3B** | Payables Customs + regressão | **DONE** |
| **I5-4** | Nationalization + Inventory + SkuPosition | **DONE** |
| **I5-5** | UX transversal | **DONE** |
| **I5-6** | E2E aceite SC-07/09/10 | **DONE** |

## Evidências

Ver [`EVIDENCIAS.md`](EVIDENCIAS.md). Screenshots I5-6: `screenshots/j5-01`…`j5-15`.
