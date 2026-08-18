# J4-FIN-4 — Plano de execução (espelho do mestre)

Espelho de [`fin-4_cronograma_33dac719.plan.md`](../../../.cursor/plans/fin-4_cronograma_33dac719.plan.md). Não é plano concorrente.

| Campo | Valor |
|---|---|
| Campanha | FIN-4 — cronograma de pagamento no pedido |
| Status F0 | **RATIFICADO** — execução autorizada 2026-08-13 |
| Status campanha | **DONE** (F0–F6) 2026-08-13 |
| Owner | Orders |
| Alembic | **025** (revisa `024_payment_purpose`; backfill NONE) |
| Blueprint | **0.2.19** |
| Roadmap | **0.5.114** |
| Runtime operação | `:8081` / `epic_v2` — **não resetar**; 025 aplicado additivamente |
| Testes | `epic_v2_test` — pytest **530 passed** |

## Fatias

| Fatia | Status |
|---|---|
| F0 DECs | DONE |
| F1 domínio + 025 | DONE |
| F2 reporting `schedule` | DONE — KPIs paid/advanced/fx intocados |
| F3 UI comercial + cockpit + OpenAPI | DONE |
| F4 conciliação + J | DONE |
| F5 Blueprint 0.2.19 + UI/UX pontual §21.4 | DONE |
| F6 percurso UI + Roadmap A/B | DONE — sample `F4-WALK-f5c640a8` id 36; 589/CICLO-001 intactos |

Handoff: [`J4_FIN4_ADVISOR_HANDOFF.md`](J4_FIN4_ADVISOR_HANDOFF.md).
| Owner | Orders |
| Alembic previsto | **025** (head encontrado = `024_payment_purpose`) |
| Runtime operação | `:8081` / `epic_v2` — **não resetar** |
| Testes | `epic_v2_test` (`postgresql://postgres@localhost:5433/epic_v2_test`) |

## F0 — Ambiente (início da execução)

- Branch `main`, HEAD `3b10deb`. WIP material preservado (CICLO-FIX, G2–G5, ROADMAP 0.5.113, 024 untracked). Sem `reset`/`clean`.
- Alembic na árvore: `001…019, 021…024`. **020 ausente** (RUX-3A isolada). Head de código = `024`.
- `EXPECTED_ALEMBIC_REVISION` no start = `024` → FIN-4 cria **025** revisando 024.
- Grafo inalterado: Orders ↛ Billing/Treasury. Treasury→Orders (FIN-1) permanece. Reporting lê os três.

## DECs ratificadas (advisor)

- **DEC-F4-WHEN:** `due_date` e/ou `condition_text`; ≥1; sem enum
- **DEC-F4-MODE:** um modo por cronograma, inferido das linhas; xor percent/amount; sem coluna em Order
- **DEC-F4-BASE:** PERCENT com total incompleto; Σ=100%; derivado `null` se base `null`; nunca zero inventado
- **DEC-F4-AMOUNT:** moeda do Order; DRAFT pode divergir; confirm/CONFIRMED set exigem Σ=total **quando** total calculável; se total `null`, preservar (delta `null`, UI não diz coerente nem delta zero)
- **DEC-F4-DIVERGE:** mudar itens não muta cronograma; confirm aplica gate AMOUNT
- **DEC-F4-EDIT:** DRAFT com `orders:write`; CONFIRMED exige reason+audit; CANCELLED/CLOSED bloqueado
- **DEC-F4-COVER:** Fattura não cobre/consome cronograma
- **DEC-F4-KPI:** sem KPI “Previsto”
- **DEC-F4-INGEST:** sem parser Ordine→cronograma
- **DEC-F4-FX:** sem FxPlanRate no cronograma

## Arquitetura (não reabrir)

Cronograma = planejamento Orders. ≠ Payment ≠ Allocation ≠ Payable. Não entra em AP / paid / advanced_credit / fx_exposure. ADVANCE permanece ADVANCE. SETTLEMENT não é reclassificado. Camadas paralelas.

## Fatias

F1 domínio+025 → F2 reporting → F3 UI → F4 conciliação → F5 Blueprint 0.2.19 + UI/UX pontual → F6 gates+percurso UI+Roadmap A/B.

Escopo negativo: 3A/020, J#5-REC, J#6, CUSTOMS_FUNDING settlement, redesign, unbind, 589 restante, backlogs CICLO.
