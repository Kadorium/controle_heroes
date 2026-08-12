# RUX-3B-2a — golden / pytest diff

| Item | Valor |
|---|---|
| Baseline half-1 | **447 passed** (`rux3b-pytest-full-run3.txt`) |
| Esta fatia | **451 passed** (`rux3b2a-pytest-full.txt`) |
| Delta | **+4** testes novos |

## Novos testes

| Teste | Gate |
|---|---|
| `test_rux3b2a_empty_catalog_commit_commitment_with_unit` | create_supplier + 2 COMMITMENT (unit=PZ) + invoice bloqueado |
| `test_rux3b2a_reimport_matcher_finds_supplier` | matcher acha Heroes; sem create_supplier |
| `test_rux3b2a_supplier_exists_link_required_409` | 409 `commit_supplier_link_required` |
| `test_rux3b2a_injected_failure_zero_writes` | all-or-nothing + zero órfão |

Arquivo: `v2/tests/test_ingestion_rux3b2a_commitment_commit.py`

## Goldens de extração / issues

Sem alteração de goldens de adapter (MATH_EXPORT_N31 / SUPPLIER_NOT_FOUND / UNMATCHED_SKU).  
Diff de comportamento: preview/commit Ordine deixa de emitir `skip_item_*` por ausência de Product.
