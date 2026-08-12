# J3-RUX-2R-a — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | RUX-2R-a (unsqueeze + math L2/L5 + skip_order + C4 + UI A1/A2 + governança) |
| Status | **DONE** |
| Data | 2026-08-06 |
| Runtime | `http://127.0.0.1:8081` · DB `epic_v2` · Importação **#3** (re-ingest Ordine 589) |

## Aceite anterior

Slice fino **APROVADO** (badge, 3 blocos, 1 pendência real).

## Entregas

### Parte A (UI)
- **A1:** Resumo / Fattura operador usam `formatDateOnly` → `04/06/2026`.
- **A2:** Fornecedor primeiro; aviso math só se L2/L5 real (tom neutro/`details`).

### Parte B (governança)
- Plano mestre sincronizado (slice ACEITO; 2R/3* = `pending` não `cancelled`; 2R-a autorizado).
- Espelho `J3_EXECUTION_PLAN.md` alinhado.
- Roadmap tabela §4: Ingestão **ENTREGUE** + **REOPENED_FOR_RUX** (não “DONE I0…I7”).

### Parte C (adapter)
1. **Unsqueeze** só `description.normalized`; raw intacto. Ex.: raw `ra c c hette…` → norm `racchette 2027 GRAFICATE`.
2. **Math:** só L2 (`MATH_LINES_VS_TAX_BASES`) + L5 (`MATH_LINE_TOTAL_MISMATCH`) + INFO `MATH_EXPORT_N31`. Removidos L3/L4/`MATH_TOTAL_MISMATCH`.
3. **skip_order:** `Pedido não será criado até resolver o fornecedor.` quando order_number existe.
4. **C4:** testes dual-form PASS — supplier `"Heroe's Srl"` em fragmentado e unsqueezed; PDF real OK. **C4 não quebrou** (unsqueeze permanece description-only).
5. Savepoint `_safe_catalog` em `match_catalog` — evita abortar UoW quando `epic_v2` não tem `suppliers.tax_id` (schema Catalog atrasado; não é migration nesta fatia).

## Golden i3 — alteração DELIBERADA

`test_golden_math_export_n31_no_false_taxable_warning` agora também exige ausência de `MATH_LINE_VAT_NATURE` e `MATH_TOTAL_MISMATCH` (além de L3 composition). Motivo: RUX-2R-a remove emissão dessas camadas — **não** é “teste afrouxado”.

i4: sem cascata de falha reportada na suíte i3+i4 (58 passed na rodada anterior).

## Gate

| Critério | Resultado |
|---|---|
| Resumo legível `racchette 2027 GRAFICATE` | PASS |
| Data `04/06/2026` | PASS |
| 1 pendência real (fornecedor); **zero** aviso math | PASS |
| Heroe's extraído | PASS |
| pytest i3 | 28 passed |
| Screenshot | [`screenshots/j3-rux-2ra-ordine-589.png`](screenshots/j3-rux-2ra-ordine-589.png) |
| Browser | Cursor/Chromium Electron (mesmo runtime slice) |

## raw vs normalized (doc #3)

| | |
|---|---|
| raw | `ra c c hette 2027 GR AFIC AT E` |
| normalized | `racchette 2027 GRAFICATE` |

## Pendências / não autorizado

RUX-2R-b (reextract UI, Modelo B, readiness), RUX-3*, Orders nullable, L3 SCONTI (RUX-4), migration Catalog `tax_id` em `epic_v2`.

## Próxima etapa

**Parar.** RUX-2R-b só com autorização explícita.

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md (0.5.79); docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; plano mestre j3-rux_operational_ux; este handoff
- Evidence: docs/v2/etapa-j3/screenshots/j3-rux-2ra-ordine-589.png
- Roadmap status: 0.5.79 — RUX-2R-a DONE
- Next TODO: aguardar auth RUX-2R-b (ou aceite manual)
- Return to advisor: docs/v2/etapa-j3/J3_RUX_2RA_ADVISOR_HANDOFF.md
```
