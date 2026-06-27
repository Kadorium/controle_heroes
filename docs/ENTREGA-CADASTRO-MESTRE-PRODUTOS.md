# Entrega — Cadastro Mestre de Produtos

**Data:** 2026-06-25  
**Alembic head:** 011  
**Decisão UX:** híbrido — drawer na lista + rota `/cadastros/produtos/:id` com **9 abas** (incl. Ordens de importação)

---

## Resumo

Redesign da tela **Cadastros > Produtos** de formulário mínimo (3 colunas) para catálogo operacional com busca, filtros, visibilidade (operacionais/arquivados/anulados), drawer rápido, detalhe completo, arquivar/restaurar/anular, ordens vinculadas, audit log campo a campo e validações por etapa na importação.

**Fora deste escopo (fase 2):** import/export XLSX, upload de fotos integrado na aba (usa infra `/api/documents` existente).

---

## Mudanças principais

### Backend
- Migração [`011_product_master_fields.py`](../alembic/versions/011_product_master_fields.py): lifecycle, grupo/subgrupo, fiscal, arquivamento, índices, backfill `product_group='Sem grupo'`
- Serviço [`app/services/product_catalog.py`](../app/services/product_catalog.py)
- API expandida [`app/api/products.py`](../app/api/products.py): `/catalog`, `/detail`, `/orders`, `/audit`, `/archive`, `/restore`, `/export/csv`
- Permissões: `products:read|write|ncm_change|archive|restore|cancel|import`
- Validação em [`app/api/importations.py`](../app/api/importations.py) ao adicionar item com produto descontinuado/arquivado
- PATCH NCM exige motivo + audit `field_changed` quando produto já usado

### Frontend
- [`frontend/src/pages/ProductsPage.tsx`](../frontend/src/pages/ProductsPage.tsx) — lista profissional
- [`frontend/src/pages/products/ProductQuickDrawer.tsx`](../frontend/src/pages/products/ProductQuickDrawer.tsx)
- [`frontend/src/pages/products/ProductDetailPage.tsx`](../frontend/src/pages/products/ProductDetailPage.tsx) — 9 abas
- Rota aninhada em [`router.tsx`](../frontend/src/router.tsx) (react-router existente preservado)
- `ProductCombobox` / Nova Ordem: só produtos `ACTIVE` via `for_combobox=true`
- DISCONTINUED fora do combobox; uso em ordem exige override + motivo na API

---

## Testes executados

| Comando | Resultado |
|---------|-----------|
| `alembic upgrade head` | OK → 011 |
| `pytest tests/test_product_catalog.py -q` | 9 passed |
| `pytest tests/ -q` | **214 passed** |
| `npm run build` | OK |

---

## Evidências

- Lista: busca, chips de filtro, export CSV client-side, colunas densas, badges de pendência
- Drawer: criar/editar SKU, nome, grupo, status, NCM
- Detalhe: 9 abas; aba **Ordens de importação** com busca e link para hub
- Arquivar: some da visibilidade `active`; restaurar reversível
- Anular: soft delete com motivo; filtro `cancelled`

---

## Bugs encontrados / corrigidos

1. **LandedCostSkuAllocation** não tem `product_id` — corrigido join via `importation_item_id`
2. **Validação importação** bloqueava produtos com grupo `"Sem grupo"` (backfill) — ajustado para só bloquear grupo vazio
3. **Import path** errado em `ProductsPage.tsx` — corrigido para build Vite

---

## Pendências / próxima etapa

1. **XLSX** import/export (fase 2)
2. Upload de foto na aba Fotos (wire `POST /api/documents/upload` entity_type=product)
3. Seleção de fornecedor padrão no detalhe (combobox suppliers)
4. Validations customs/LC hooks (landed cost weight method)
5. E2E Playwright dedicado `products-catalog.spec.ts`
6. Redesign **Fornecedores** no mesmo padrão

---

## Lacunas checklist

- **F3-002** reaberto → **IN_PROGRESS** (evidência: nova UI + API catalog)
- **F3-002b** cadastro mestre → **DONE** (esta entrega)
- **L-006** campos SKU → **PARTIAL** (NCM/peso/volume + readiness; política fiscal completa pendente)
