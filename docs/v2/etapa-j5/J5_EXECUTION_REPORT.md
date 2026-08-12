# J#5 — Relatório de execução (patch fechamento + I5-6)

| Campo | Valor |
|---|---|
| Fase | Aduana + Inventory (J#5) |
| Checkpoint | **Patch C0…C5 DONE** (core I5-6 preservado) |
| Data | 2026-08-04 |
| Roadmap | **0.5.63** |
| Blueprint | **0.2.16** |
| Alembic head | `015_nationalization_inventory` (sem migration nova) |
| Classificação UI | **ACCEPTED_WITH_BACKLOG** — [`UI_ACCEPTANCE_J5.md`](UI_ACCEPTANCE_J5.md) |
| DEC | [`patch-close/DEC_ALT_B_CUSTOMS_PAYMENT.md`](patch-close/DEC_ALT_B_CUSTOMS_PAYMENT.md) |

## 1. Gates técnicos (patch)

| Gate | Comando / escopo | Resultado |
|---|---|---|
| pytest Inventory/Customs/Reporting/Billing/Treasury/Arch | `logs/patch-close-pytest-full.txt` | **PASS** — 83 |
| architecture (billing/reporting ↛ customs) | `tests/architecture/` | **PASS** |
| generate:api + api-drift | `npm run generate:api` / `check:api-drift` | **PASS** |
| vitest inventory labels | `vitest run src/features/inventory` | **PASS** — 3 |
| tsc + build | via `e2e:j5` | **PASS** |
| e2e:j5 | 4 specs | **PASS** — 4 |
| e2e:inc-6 | regressão Order-to-Pay | **PASS** — 1 |
| e2e:logistics | regressão J#4 | **PASS** — 4 |

## 2. Patch C0…C5

| ID | Escopo | Status |
|---|---|---|
| J5-C0 | DEC Alt. B + matriz draft | **DONE** |
| J5-C1 | KPIs `kpis_by_currency`; drawer por origem; `source_id`; GET funding; `/customs/funding/:id`; `/payables` | **DONE** |
| J5-C2 | Isolamento Payment Customs (notice + backend) | **DONE** |
| J5-C3 | RECLASS pareado; SkuPosition dimensional; UX Inventory | **DONE** |
| J5-C4 | SC-10 UI + shots 1366 | **DONE** |
| J5-C5 | Docs Blueprint/Roadmap + gates | **DONE** |

## 3. Migrations 011–015 (fechadas — não reabertas)

Head permanece **015**.

## 4. Decisões (patch)

| ID / tema | Estado |
|---|---|
| DEC-J5-CLOSE-ALT-B | **Canônica** — Payable Customs = obrigação registrada; sem liquidação Treasury nesta release |
| KPIs AP | Por moeda; sem soma cross-currency; campos monetários agregados removidos |
| Nav AP→Customs | Opção B — GET público funding + redirect FE |
| RECLASS | Pareado OUT+IN; conservação física SC-10 |
| SkuPosition | Dimensões físicas/aduaneira/logística; stubs = “Não disponível” |

## 5. Backlog

**`Treasury settlement for CUSTOMS_FUNDING`** — ver Roadmap §8.

## 6. Próxima ação

**Planejar J#3** — não iniciar execução.
