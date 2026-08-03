# Grupo V0 — Fundação real de apresentação

## Estado

**DONE** (escopo V0). Etapa 9V permanece **PARTIAL**. Aceite visual Horizon A permanece **NOT_ACCEPTED**.

## Objetivo

Primitives de apresentação corretos + shell + enrichment Payments `supplier_name`, demonstrados em Pagamentos. V1–V3 fora de escopo.

## Hipóteses iniciais (execução)

| # | Hipótese | Veredito | Evidência |
|---|---|---|---|
| 1 | branch = main | Confirmada | `git rev-parse` |
| 2 | WIP Etapa 9 preservado | Confirmada | status sujo pré/pós |
| 3 | Roadmap 0.5.30 Etapa 9 DONE | Confirmada → corrigida 0.5.31 | cabeçalho |
| 4 | docs/README stale | Confirmada → sincronizado | README |
| 5 | etapa-9 A–D DONE | Confirmada (funcional) | README etapa-9 |
| 6 | UI/UX/Handoff/MCK/Sistema intactos | Confirmada | sem edits nesses artefatos |
| 7 | frontend em v2/frontend | Confirmada | path |
| 8 | MoneyDisplay passthrough | Confirmada → corrigido | formatMoney |
| 9 | sem formatador de datas | Confirmada → criado | formatDateOnly |
| 10 | Payments sem supplier_name | Confirmada → enrich BE | PaymentResponse |
| 11 | 9V não iniciada | Confirmada → iniciada nesta ação | docs/v2/etapa-9v |

## Decisões técnicas

| Tema | Decisão | Evidência |
|---|---|---|
| Enrichment Payments | `catalog_public.get_suppliers_bulk` no router Treasury (ALLOWED_DEPS: treasury→catalog) | Mesmo padrão Orders/Billing list |
| Campo | `supplier_name: str \| None` aditivo em `PaymentResponse` | Sem migration |
| Lista | 1 bulk por request — sem N+1 de suppliers | `list_payments` |
| Detail/create | `_payment_response` resolve nome se não passado | bulk de 1 id |
| Formatadores | `ui/format.ts` — money/rate/date-only/datetime | Sem Intl currency mode |
| Status | `ui/statusLabels.ts` por entidade | REGISTERED→Registrado |
| Fixture visual | E2E cria supplier fixo `Heroes Metalúrgica LTDA` + payment 400 EUR @ 2026-07-23 | `i9v-v0-foundation.spec.ts` |

## Arquivos

**FE:** `ui/format.ts`, `statusLabels.ts`, `EntityRef.tsx`, `RowLink.tsx`, `MoneyDisplay.tsx`, `StatusBadge.tsx`, `index.tsx`, `index.css`, `AppShell.tsx`, `FxPanels.tsx` (strip), `PaymentsListPage.tsx`, `treasuryApi.ts`, OpenAPI gerado

**BE:** `v2/app/treasury/routes.py`

**Testes:** `format.test.ts`, `ui.foundation.test.tsx`, `PaymentsPages.test.tsx`, `test_treasury_api.py` (enrichment), `e2e/i9v-v0-foundation.spec.ts`

**Docs:** Roadmap 0.5.31, `docs/README.md`, `docs/v2/etapa-9/README.md`, `docs/v2/etapa-9v/`

## Gates

| Gate | Resultado |
|---|---|
| Unit formatters/status/EntityRef | **PASS** — 41 tests |
| Pytest enrichment + boundaries | **PASS** — 5 passed |
| Typecheck + build | **PASS** |
| E2E epic_v2_test V0 + shell + grupo-C | **PASS** — 3 passed |
| Visual 1366 shell+payments | Capturado — ver matriz |
| Visual 1440 shell+payments | Capturado — ver matriz |

Log: `logs/grupo-V0-e2e.txt`

## Screenshots

- `screenshots/v0-shell-1366.png`
- `screenshots/v0-payments-1366.png`
- `screenshots/v0-shell-1440.png`
- `screenshots/v0-payments-1440.png`

## Comparação visual V0 (primitives)

Referências: shell MCK transversal · Handoff SCR-002 · Handoff SCR-010 · MCK-001 (análogo fila) · MCK-006 (residual).

| Item | Veredito |
|---|---|
| Hierarquia do shell | **PASS** parcial — Compras/Financeiro + footer FX/Sair; densidade melhorada vs pré-V0 |
| Densidade | **PASS** parcial — gaps reduzidos; ainda não pixel-perfect MCK (dívida V1 polish) |
| Estado ativo | **PASS** — barra + fundo no item ativo |
| Data | **PASS** — `23/07/2026` (sem ISO) |
| Dinheiro | **PASS** — `EUR 400,00` / `EUR 0,00` |
| Moeda | **PASS** — código explícito em Valor/Alocado/Residual |
| Status | **PASS** — `Registrado` + semântica information (não só cor) |
| Fornecedor | **PASS** — `Heroes Metalúrgica LTDA` (não `#id`) |
| Ação de linha | **PASS** parcial — `RowLink` DS; polish visual completo = V1 |
| Copy técnica | **PASS** na lista — subtitle operacional; Create≠Allocate removido de SCR-010 list |
| Diferenças remanescentes | Filtros/Ref/KPI/colunas SCR-010 completas = **V1**; demais SCR = V1–V3; shell ainda com whitespace de conteúdo |

## Dívidas (fora de V0)

- Migração das outras 11 superfícies para formatadores/StatusBadge/EntityRef
- Filtros e colunas completas de Pagamentos (V1)
- PaymentCreate/Detail ainda com copy técnica Create≠Allocate
- FX panels labels EN / Inc-4A
- Aceite visual Horizon A

## Rollback

Reverter arquivos FE/BE listados; campo `supplier_name` é aditivo (compatível).
