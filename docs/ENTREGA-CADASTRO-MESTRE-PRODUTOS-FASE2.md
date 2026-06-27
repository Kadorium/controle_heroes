# Entrega — Cadastro Mestre de Produtos (Fase 2)

**Data:** 2026-06-25  
**Alembic head:** 011 (sem nova migração)  
**Escopo:** seleção em massa, import/export CSV+XLSX, grade enriquecida, abas detalhe completas

---

## Resumo

Complemento da fase 1 com **checkbox + barra de ações em massa** (arquivar, restaurar, descontinuar, reativar, anular, exportar selecionados), endpoints bulk transacionais, import CSV/XLSX preview+commit, export XLSX, colunas extras na lista com `EditableCell`, miniatura de foto, e abas do detalhe extraídas (fornecedor, custos, fotos, anular).

---

## Backend

| Artefato | Entrega |
|---|---|
| [`app/services/product_catalog.py`](../app/services/product_catalog.py) | `BulkActionResult`, `bulk_*`, `photo_attachment_id` no catalog |
| [`app/services/product_import.py`](../app/services/product_import.py) | Preview/commit CSV e XLSX |
| [`app/api/products.py`](../app/api/products.py) | `POST /bulk/*`, `POST /import/*`, `GET /export?format=xlsx` |
| [`app/schemas_import.py`](../app/schemas_import.py) | Schemas bulk + import |

---

## Frontend

| Artefato | Entrega |
|---|---|
| [`ProductsPage.tsx`](../frontend/src/pages/ProductsPage.tsx) | Checkbox, bulk bar, import modal, export CSV/XLSX, colunas extras, inline edit |
| [`useProductSelection.ts`](../frontend/src/pages/products/useProductSelection.ts) | Hook seleção + elegibilidade |
| [`ProductBulkActionBar.tsx`](../frontend/src/pages/products/ProductBulkActionBar.tsx) | Barra flutuante |
| [`ProductBulkConfirmModal.tsx`](../frontend/src/pages/products/ProductBulkConfirmModal.tsx) | Confirmação com motivo |
| [`ProductImportModal.tsx`](../frontend/src/pages/products/ProductImportModal.tsx) | Preview → commit |
| [`ProductDetailTabs/`](../frontend/src/pages/products/ProductDetailTabs/) | 9 abas extraídas |
| [`productCatalogUtils.ts`](../frontend/src/pages/products/productCatalogUtils.ts) | Helpers bulk + export |

---

## Testes

| Comando | Resultado |
|---|---|
| `pytest tests/test_product_catalog.py -q` | 14 passed |
| `npm run build` | OK |
| `npm run test` | 12 passed |

---

## Regras UX bulk

- Anular = soft delete (nunca delete físico)
- Motivo obrigatório: arquivar e anular (unitário e massa)
- Produtos inelegíveis listados como ignorados no modal
- Aviso extra ao anular SKUs com ordens vinculadas

---

## Pendências fase 3

- Drag-and-drop colunas configuráveis
- Selecionar todos os N resultados server-side (>500)
- E2E Playwright dedicado (opcional)
