# RUX-3B (1/2) — golden / assert diff — 2026-08-06

Rodada: `pytest` completo → **447 passed** (`logs/rux3b-pytest-full-run3.txt`).

## Goldens IR / math

| Teste | Diff |
|---|---|
| i3 math N3.1 / i4 math N3.1 | **NONE** (lista positiva inalterada) |
| i3 `test_golden_ordine_589_issue_codes_exact` | Asserts **iguais**; teste agora **isola** `list_suppliers`/`list_products` vazios via monkeypatch — suíte poluía com `Heroes SPA` etc. e quebrava a semântica “catálogo vazio” do B3. **Deliberado.** |

## Asserts / helpers alterados (DELIBERADO)

| Item | Motivo |
|---|---|
| i3/i4/i7 `_ensure_supplier*` | Preferir nome **exato** `Heroe's Srl` (não `suppliers[0]` de `q=Heroe`) |
| ordine/fattura `match_catalog` | Se múltiplos hits, preferir **nome exato** antes de AMBIGUOUS |
| i7 head test | `019` → **`021`** + `EXPECTED_ALEMBIC_REVISION` |
| a2 `test_migration_010_revises_009` | Remove assert `head==010` (já obsoleto desde 011); novo `test_migration_021_revises_019` |
| NOVO `test_orders_rux3b_commitment.py` | Gates COMMITMENT / confirm Audit / invoice bloqueado / regressão PRODUCT |

## OpenAPI

- Regenerado: `openapi.json` + `schema.ts` (volume grande = catch-up de drift prévio).
- `client.ts` **não** mudou.
- `OrderItemResponse.product_id: number \| null` + `line_kind` + `external_code`.
