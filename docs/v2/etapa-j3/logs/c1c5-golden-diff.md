# Golden diff — i3 / i4 (esta rodada)

## test_ingestion_i3.py
- `test_golden_math_export_n31_no_false_taxable_warning`: de asserts por AUSENCIA (varios `not in`) para lista POSITIVA exata `codes == [\"MATH_EXPORT_N31\"]`.
- NOVO `test_golden_ordine_589_issue_codes_exact`: lista positiva `[MATH_EXPORT_N31, SUPPLIER_NOT_FOUND, UNMATCHED_SKU, UNMATCHED_SKU]`.
- `test_matching_with_catalog_resolves_products` → `test_matching_with_catalog_still_unmatched_iv_lines` (Q3=B; sem SUGGESTED_SKU_MATCH / refs).
- `_ensure_products`: sem `upsert_supplier_product_ref` / `sku=None`.

## test_ingestion_i4.py
- `test_golden_math_export_n31_no_false_taxable_warning`: lista POSITIVA exata `codes == [\"MATH_EXPORT_N31\"]` (antes: ausencia + contains).

## Resultado pytest (esta rodada)
60 passed — log: `docs/v2/etapa-j3/logs/c1c5-pytest-i3-i4.txt`
