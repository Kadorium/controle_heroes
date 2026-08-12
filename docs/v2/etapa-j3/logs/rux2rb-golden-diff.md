# RUX-2R-b — golden diff (i3 + i4) — 2026-08-06

Rodada: `pytest tests/test_ingestion_i3.py tests/test_ingestion_i4.py` → **62 passed**.

## Goldens de extração / math

| Teste | Antes (C1–C5) | Nesta rodada | Diff |
|---|---|---|---|
| i3 `test_golden_math_export_n31_no_false_taxable_warning` | `codes == ["MATH_EXPORT_N31"]` | igual | **NONE** |
| i3 `test_golden_ordine_589_issue_codes_exact` | `[MATH_EXPORT_N31, SUPPLIER_NOT_FOUND, UNMATCHED_SKU, UNMATCHED_SKU]` | igual | **NONE** |
| i4 `test_golden_math_export_n31_no_false_taxable_warning` | `codes == ["MATH_EXPORT_N31"]` | igual | **NONE** |

RUX-2R-b não altera adapters nem matching — goldens de IR **deliberadamente inalterados**.

## Asserts de commit alterados (DELIBERADO)

| Teste | Antes | Depois | Motivo |
|---|---|---|---|
| i3 `test_commit_creates_order_draft` | status ∈ {SUCCEEDED, PARTIAL} | **SUCCEEDED** only; verifica arquivo promovido (sem `.pending`) | Tudo-ou-nada; caminho feliz não produz PARTIAL |
| i3 `test_get_commit_attempt_status` | status ∈ {SUCCEEDED, PARTIAL, FAILED, UNKNOWN} | **SUCCEEDED** | Commit feliz do setup |
| i3 `test_commit_injected_failure_*` | (não existia / Modelo B) | **NOVO**: falha injetada → FAILED + zero write + zero órfão; retry → SUCCEEDED | Gate RUX-2R-b |
| i3 `test_commit_failure_leaves_no_pending_file` | (não existia) | **NOVO**: create_order falha → sem `.pending` | FS temp→promote |
| i3 helpers `_bind_catalog_on_ir` | order_number fixo 589 | `order_number=f"589-{doc_id}"` | Código Order único (`ING-…`); antes colisão virava PARTIAL silencioso |
| i4 `test_policy_a_creates_invoice_draft` | status ∈ {SUCCEEDED, PARTIAL}; idempotência em teste separado | **SUCCEEDED** + replay no mesmo teste | PARTIAL removido do caminho Fattura |
| i4 `test_policy_a_idempotent` | replay feliz com mesma key | **SUBSTITUÍDO** por `test_policy_a_duplicate_invoice_is_all_or_nothing` | Colisão invoice 202: agora FAILED all-or-nothing (antes PARTIAL com Document persistido) |
| i4 `test_policy_c2_creates_invoice_with_confirm` | status ∈ {SUCCEEDED, PARTIAL} | **SUCCEEDED** | Mesma razão |

## PARTIAL que permanece (fora do escopo)

- Numerario / XLSX / Dossier ainda podem emitir PARTIAL (tabelas compartilhadas).
- CHECK DB e enum `PARTIAL` **não** removidos — só Ordine/Fattura deixam de produzir.
