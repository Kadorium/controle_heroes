# Inc-6 — E2E, goldens e aceite Order-to-Pay

**STATUS:** DONE  
**Data:** 2026-07-30  
**Banco E2E:** `epic_v2_test` @ `:8082`  
**Alembic head:** `006_fx_integrity`  
**Branch:** `main` (WIP pré-existente preservado; sem commit automático)

## Resumo

| Gate | Resultado |
|---|---|
| pytest | **103 passed**, 0 xfailed |
| characterization + arch | **15 passed** |
| RBAC (orders/billing/fx) | **15 passed** |
| OpenAPI drift | up to date |
| Vitest | **58 passed** |
| typecheck / build | OK |
| `e2e:horizon-a` | **18 passed** |
| `e2e:inc-6` | **1 passed** |
| BLOCKERS / MAJORS | nenhum |

## Ownership parse_it

- Localização: `v2/app/ingestion/parse_it.py` + `public.py`
- Grafo: nó `ingestion` com `ALLOWED_DEPS=∅`; `.parse_it` em INTERNAL_SUFFIXES
- Sem routes/models/adapters/migrations (J#3 permanece TODO)

## Proveniência dos goldens

| Arquivo | Tipo | Fonte dos inputs | Fonte dos expected | Regra | Revisão |
|---|---|---|---|---|---|
| `parse_it_number.v1.json` | Characterization V1 | exporter cases | V1 `parse_it_number` | locale IT/EN; null≠0 | Equivalência V2 PASS |
| `parse_it_date.v1.json` | Characterization V1 | exporter cases | V1 `parse_it_date` | dd/mm; needs_review | Equivalência V2 PASS |
| `billing_line.v2.json` | Contract V2 | casos manuais | DEC-SCONTO-ITEM + HALF_UP 2dp | NONE/UNIT/PERCENT; null tipo | Revisado I6-1 |
| `scadenze_split.v2.json` | Contract V2 | net + percents | residual última; Σ=net | %Σ=100 | Revisado I6-1 |
| `fx_canonical.v2.json` | Contract V2 | rates canônicos | −40/−90/−130 documentados | fx_money | Revisado I6-1 |

Xfail `test_v2_parse_equivalence_placeholder` **removido** (substituído por comparação real).

## E2E vertical (`npm run e2e:inc-6`)

Comprova SC-01…04 + idempotência + excesso + FX canônico + Documents + Audit + AP + Cockpit.  
Manifest: `e2e/suites/inc-6.txt` · Spec: `e2e/inc6-order-to-pay.spec.ts`

## Classificação de falhas durante execução

| Classe | Caso | Ação |
|---|---|---|
| B | HTTP 201 vs 200 em creates | `expectOk` 2xx |
| B | Formato decimal `-40.0000` vs `-40.00` | assert numérico exato |
| B | Horizon A flaky sob contenção DB com pytest paralelo | reexecução limpa → 18p |
| B | RBAC ERROR sob schema parcial durante e2e_prepare | reexecução em `epic_v2_test` → 15p |

## Ausências confirmadas

- Sem `inventory` / `logistics` / `customs` packages
- Ingestão plena (adapters/staging) **não** iniciada — só foothold `parse_it`
- Horizon B1 **não** executado; sem migration B1
- `epic_v2` (ops) não resetado

## Logs

- `pytest-final.txt`
- `characterization-arch.txt`
- `rbac.txt`
- `openapi-drift.txt`
- `vitest.txt` / `tsc.txt` / `build.txt`
- `e2e-horizon-a.txt`
- `e2e-inc-6.txt`
- `goldens-list.txt` / `app-packages.txt`
