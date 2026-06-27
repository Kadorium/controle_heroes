# Guia — Tela de Cadastro Mestre de Produtos

Documento de referência para operadores e desenvolvedores. Descreve **todas as opções, campos e ações** da nova tela de produtos e como cada parte se conecta ao **frontend** e ao **backend**.

**URLs:**
- Lista: `/cadastros/produtos`
- Detalhe: `/cadastros/produtos/:id`

**Decisão de UX:** modelo híbrido — **drawer** na lista para criar/editar campos principais; **página dedicada** para o cadastro completo (**5 abas**).

---

## 1. Mapa de arquivos

### Frontend

| Arquivo | Função |
|---|---|
| `frontend/src/pages/ProductsPage.tsx` | Lista principal (busca, filtros, grade, bulk, import/export) |
| `frontend/src/pages/products/ProductQuickDrawer.tsx` | Drawer lateral — criar/editar rápido |
| `frontend/src/pages/products/ProductDetailPage.tsx` | Shell do detalhe com **5 abas** (Identificação, Fiscal e Logística, Fornecedores, Ordens e Custos, Documentos e Histórico) |
| `frontend/src/pages/products/ProductDetailTabs/*.tsx` | Conteúdo de cada aba |
| `frontend/src/pages/products/ProductBulkActionBar.tsx` | Barra de ações em massa |
| `frontend/src/pages/products/ProductBulkConfirmModal.tsx` | Confirmação com motivo (arquivar/excluir) |
| `frontend/src/pages/products/ProductImportModal.tsx` | Importação CSV/XLSX |
| `frontend/src/pages/products/productCatalogUtils.ts` | Labels, filtros, elegibilidade bulk, export CSV client-side |
| `frontend/src/pages/products/useProductSelection.ts` | Seleção por checkbox |
| `frontend/src/api.ts` → `productsApi` | Cliente HTTP de todos os endpoints |
| `frontend/src/router.tsx` | Rotas aninhadas em `/cadastros` |

### Backend

| Arquivo | Função |
|---|---|
| `app/models.py` → `Product` | Tabela `products` + campos mestre |
| `app/schemas_import.py` | Schemas Pydantic (create, update, catalog, bulk, import) |
| `app/api/products.py` | Endpoints REST |
| `app/services/product_catalog.py` | Listagem enriquecida, flags, bulk, archive/restore, ordens, audit |
| `app/services/product_import.py` | Preview e commit de CSV/XLSX |
| `app/api/importations.py` | Valida produto ao vincular item em ordem |
| `alembic/versions/011_product_master_fields.py` | Migração dos campos mestre |

---

## 2. Campos do produto (modelo de dados)

Todos persistidos na tabela `products`. Campo vazio **nunca vira zero** — peso, volume e NCM ficam `NULL` quando não informados.

| Campo (backend) | Tipo | Obrigatório | Onde aparece no frontend | Descrição |
|---|---|---|---|---|
| `sku_code` | string(64) | Sim (create) | Drawer, lista, detalhe | Código único do produto. **Imutável** após criação. |
| `description` | string(512) | Sim | Drawer (Nome), lista | Nome/descrição comercial. |
| `product_group` | string(64) | Sim (default `Sem grupo`) | Drawer, lista, aba Identificação | Grupo comercial (ex.: Raquetes). |
| `product_subgroup` | string(64) | Não | Aba Identificação | Subgrupo comercial. |
| `lifecycle_status` | string(32) | Sim (default `ACTIVE`) | Drawer, lista, aba Identificação | `ACTIVE`, `DISCONTINUED`, `DRAFT`, `ARCHIVED`. |
| `ncm` | string(16) | Não | Drawer, lista, aba Fiscal | NCM aduaneiro. |
| `category` | string(32) | Sim (default `OTHER`) | Aba Identificação (somente leitura) | Categoria operacional Heroes (Raquete, Bola…). **Distinto** de grupo/subgrupo. |
| `supplier_code` | string(128) | Não | Lista, aba Fornecedores | Código no fornecedor / Heroes. |
| `default_supplier_id` | FK suppliers | Não | Aba Fornecedores | Fornecedor padrão de compras. |
| `country_of_origin` | string(8) | Não | Aba Fiscal | País de origem (ISO, ex.: `IT`). |
| `unit_of_measure` | string(16) | Não | Aba Fiscal | Unidade (UN, CX…). |
| `fiscal_description` | text | Não | Aba Fiscal | Descrição aduaneira (não inventa NCM). |
| `fiscal_review_required` | boolean | Não (default false) | Aba Fiscal | Marca produto para revisão fiscal → badge na lista. |
| `weight_kg` | decimal | Não | Aba Logística | Peso em kg. |
| `volume_m3` | decimal | Não | Aba Logística | Volume em m³. |
| `launch_date` | date | Não | Aba Identificação | Data de lançamento. |
| `commercial_notes` | text | Não | Aba Comercial | Notas comerciais livres. |
| `archived_at` / `archived_by_id` / `archive_reason` | — | — | Detalhe (via API) | Preenchidos ao **arquivar**. |
| `is_active` / `cancelled_at` / `cancelled_by_id` / `cancellation_reason` | — | — | Detalhe (via API) | Soft delete ao **anular**. |

### Campos calculados (só na API, não gravados em `products`)

Retornados por `GET /api/products/catalog` e `GET /api/products/{id}/detail`:

| Campo API | Origem | Uso na UI |
|---|---|---|
| `default_supplier_name` | Join com `suppliers` | Coluna Fornecedor na lista |
| `has_photo` / `photo_attachment_id` | `document_attachments` | Miniatura na lista; galeria no detalhe |
| `pending_flags` | Regras em `product_catalog.py` | Badges de pendência na lista |
| `last_importation_at` / `last_importation_po` | Agregado de ordens | Informação operacional |
| `last_landed_cost_unit` | Agregado de LC | Referência de custo |
| `orders_count` | Contagem de ordens | Drawer e lista |
| `used_in_importations` | Verifica itens de ordem | Exige motivo ao mudar NCM |

---

## 3. Lista de produtos (`ProductsPage`)

**Arquivo:** `frontend/src/pages/ProductsPage.tsx`  
**API principal:** `GET /api/products/catalog` via `productsApi.catalog()`

### 3.1 Botões do cabeçalho

| Botão | Frontend | Backend |
|---|---|---|
| **Novo produto** | Abre `ProductQuickDrawer` vazio | `POST /api/products` ao salvar |
| **Importar** | Abre `ProductImportModal` | `POST /api/products/import/preview` + `POST /api/products/import/commit` |
| **Exportar CSV** | `exportProductsCsv()` no browser (linhas visíveis) | Sem chamada API |
| **Exportar XLSX** | `productsApi.exportBlob("xlsx")` | `GET /api/products/export?format=xlsx&visibility=…` |

### 3.2 Busca global

| UI | Parâmetro API | Campos pesquisados no backend |
|---|---|---|
| Campo “Buscar SKU, nome, NCM…” | `q` | `sku_code`, `description`, `supplier_code`, `ncm` |

### 3.3 Filtros rápidos (chips)

| Chip UI | `quick_filter` API | Regra no backend (`product_catalog.py`) |
|---|---|---|
| Todos | *(omitido)* | Sem filtro extra |
| NCM pendente | `ncm_pending` | `ncm` vazio ou null |
| Sem foto | `no_photo` | Sem attachment `entity_type=product` |
| Sem peso/volume | `no_weight_volume` | `weight_kg` e `volume_m3` ambos null |
| Sem fornecedor | `no_supplier` | `default_supplier_id` null |
| Fiscal a revisar | `fiscal_review` | `fiscal_review_required = true` |
| Descontinuados | `discontinued` | `lifecycle_status = DISCONTINUED` |

### 3.4 Visibilidade (segmento)

| Opção UI | `visibility` API | O que inclui |
|---|---|---|
| Operacionais *(padrão)* | `active` | `is_active=true` e status `ACTIVE` ou `DISCONTINUED` |
| Arquivados | `archived` | `is_active=true` e status `ARCHIVED` |
| Anulados | `cancelled` | `is_active=false` |
| Todos | `all` | Qualquer registro |

### 3.5 Colunas da grade

| Coluna | Campo / origem | Interação |
|---|---|---|
| Checkbox | — | Seleção para ações em massa |
| Foto | `photo_attachment_id` | Imagem via `/api/documents/{id}/download` |
| SKU | `sku_code` | Link → detalhe; clique na linha → drawer |
| Cód. fornecedor | `supplier_code` | Somente leitura |
| Nome | `description` | Somente leitura na lista |
| Grupo | `product_group` | Ordenável |
| Status | `lifecycle_status` | Label traduzido (`STATUS_LABELS`) |
| NCM | `ncm` | Ordenável |
| Fornecedor | `default_supplier_name` | Somente leitura |
| Pendências | `pending_flags` | Badges (`PENDING_LABELS`) |
| Ordens | `orders_count` | Quantidade de ordens com o produto |

**Ordenação:** headers SKU, Nome, Grupo, Status, NCM enviam `sort` e `sort_dir` à API; há reordenação client-side adicional via `sortProducts()`.

### 3.6 Badges de pendência

Calculados no backend por `compute_pending_flags()`:

| Flag | Label na UI | Condição |
|---|---|---|
| `ncm_pending` | NCM pendente | Sem NCM |
| `no_photo` | Sem foto | Sem documento de foto |
| `no_supplier` | Sem fornecedor | Sem `default_supplier_id` |
| `no_weight_volume` | Sem peso/volume | Peso e volume ambos null |
| `fiscal_review` | Fiscal a revisar | `fiscal_review_required=true` |

---

## 4. Drawer rápido (`ProductQuickDrawer`)

**Arquivo:** `frontend/src/pages/products/ProductQuickDrawer.tsx`

Abre ao clicar em uma linha da lista ou ao clicar **Novo produto**.

| Campo UI | Campo API | Create | Update | Observação |
|---|---|---|---|---|
| SKU | `sku_code` | Editável | **Somente leitura** | Único no banco |
| Nome | `description` | Sim | Sim | |
| Grupo | `product_group` | Sim | Sim | Default `Sem grupo` |
| Status | `lifecycle_status` | Sim | Sim | ACTIVE, DISCONTINUED, DRAFT |
| NCM | `ncm` | Sim | Sim | Opcional; null se vazio |

| Ação | Frontend | Backend |
|---|---|---|
| Salvar (novo) | `productsApi.create()` | `POST /api/products` |
| Salvar (existente) | `productsApi.update()` | `PATCH /api/products/{id}` |
| Abrir detalhe | `navigate(/cadastros/produtos/{id})` | — |

Rodapé mostra `{orders_count} ordem(ns)` quando editando produto existente.

---

## 5. Detalhe completo (`ProductDetailPage`)

**Arquivo:** `frontend/src/pages/products/ProductDetailPage.tsx`  
**API de carga:** `productsApi.detail()`, `.orders()`, `.audit()`

### 5.1 Abas e campos (5 abas consolidadas)

| Aba UI | Componentes internos | Conteúdo |
|---|---|---|
| **Identificação** | `IdentificationTab` + `CommercialTab` | SKU, grupo, subgrupo, status, lançamento, categoria; notas comerciais |
| **Fiscal e Logística** | `FiscalCustomsTab` + `LogisticsTab` | NCM, fiscal, país, unidade; peso e volume |
| **Fornecedores** | `SuppliersTab` | Fornecedor padrão, código fornecedor |
| **Ordens e Custos** | `ImportOrdersTab` + `CostsTab` | Ordens vinculadas (read-only) + histórico landed cost |
| **Documentos e Histórico** | `PhotosDocumentsTab` + `HistoryAuditTab` | Fotos/documentos + audit log |

#### Identificação + Comercial

| Campo | Editável | API ao salvar |
|---|---|---|
| SKU | Não | — |
| Grupo | Sim | `product_group` |
| Subgrupo | Sim | `product_subgroup` |
| Status | Sim | `lifecycle_status` (ACTIVE, DISCONTINUED, DRAFT) |
| Lançamento | Sim | `launch_date` |
| Categoria operacional | Não (read-only) | — |
| Notas comerciais | Sim | `commercial_notes` |

| Ação | Backend |
|---|---|
| Salvar identificação | `PATCH /api/products/{id}` |
| Arquivar | `POST /api/products/{id}/archive` + `{ reason }` (mín. 3 chars) |
| Restaurar | `POST /api/products/{id}/restore` |
| Excluir (anular) | `POST /api/products/{id}/cancel` + `{ reason }` |

#### Fiscal/Aduaneiro + Logística/Embalagem

| Campo | API |
|---|---|
| NCM | `ncm` |
| Descrição fiscal | `fiscal_description` |
| País origem | `country_of_origin` |
| Unidade | `unit_of_measure` |
| Revisão fiscal (checkbox) | `fiscal_review_required` |
| Peso (kg) | `weight_kg` |
| Volume (m³) | `volume_m3` |

**Regra NCM:** se `used_in_importations=true` e NCM mudou, UI pede motivo → envia `ncm_change_reason` no PATCH. Backend retorna **422** sem motivo; grava audit com `field_changed=ncm`.

#### Fornecedores/Compras

| Campo | API |
|---|---|
| Fornecedor padrão (select) | `default_supplier_id` (lista via `GET /api/suppliers`) |
| Código fornecedor | `supplier_code` |

#### Ordens de importação + Custos

Somente leitura na grade de ordens. Busca local repassa `q` à API.

| Coluna | Campo API (`ProductOrderRow`) |
|---|---|
| Ordem | `po_number` → link `/importacoes/{importation_id}/resumo` |
| Status | `current_status` |
| Fornecedor | `supplier_name` |
| Qtd | `qty_ordered` |
| LC unit. | `landed_cost_unit` |

**Backend ordens:** `GET /api/products/{id}/orders?q=`  
**Backend custos:** `GET /api/products/{id}/cost-history`

#### Fotos/Documentos + Histórico/Auditoria

| Ação | Frontend | Backend |
|---|---|---|
| Upload foto | `documentsApi.upload(..., "product", id, "product_photo")` | `POST /api/documents/upload` |
| Galeria | `/api/documents/{id}/download` | `GET /api/documents` (list) |
| Timeline audit | — | `GET /api/products/{id}/audit` → `audit_log` where `entity_type=product` |

---

## 6. Ações em massa

**UI:** checkbox na grade + `ProductBulkActionBar` + `ProductBulkConfirmModal`

| Ação UI | Elegibilidade (frontend) | Endpoint backend |
|---|---|---|
| Arquivar | Ativo e não arquivado | `POST /api/products/bulk/archive` `{ product_ids, reason }` |
| Restaurar | Status `ARCHIVED` | `POST /api/products/bulk/restore` `{ product_ids }` |
| Descontinuar | Ativo e status `ACTIVE` | `POST /api/products/bulk/status` `{ lifecycle_status: "DISCONTINUED" }` |
| Reativar | Ativo e status `DISCONTINUED` | `POST /api/products/bulk/status` `{ lifecycle_status: "ACTIVE" }` |
| Excluir | `is_active=true` | `POST /api/products/bulk/cancel` `{ product_ids, reason }` |
| Exportar CSV | Todos selecionados | Client-side (`exportProductsCsv`) — sem API |

Resposta bulk: `{ succeeded: number[], skipped: [{id, reason}], failed: [{id, error}] }`.

---

## 7. Importação CSV/XLSX

**UI:** `ProductImportModal.tsx`  
**Backend:** `app/services/product_import.py`

### Colunas mínimas (CSV padrão)

`sku_code`, `description`, `product_group`, `lifecycle_status`

### Colunas opcionais

`ncm`, `product_subgroup`, `supplier_code`, `country_of_origin`, `unit_of_measure`, `weight_kg`, `volume_m3`, `category`, `launch_date`, `fiscal_description`, `commercial_notes`

### Planilha Heroes (aliases)

O import reconhece também cabeçalhos como `sku_sugerido`, `nome_produto`, `grupo`, `subgrupo`, `status_produto`, `pais_origem`, `peso_kg`, etc. (`HEROES_FIELD_ALIASES` em `product_import.py`). Ex.: `ITALIA` → `IT`.

| Etapa | Endpoint |
|---|---|
| Preview | `POST /api/products/import/preview` (multipart `file`) |
| Commit | `POST /api/products/import/commit` `{ rows, confirm: true }` |

---

## 8. Status do produto — arquivar vs descontinuar vs anular

| Ação | Campo alterado | Lista padrão | Nova ordem / combobox | Reversível |
|---|---|---|---|---|
| **Descontinuar** | `lifecycle_status=DISCONTINUED` | Visível (badge) | Bloqueado* | Sim → ACTIVE |
| **Arquivar** | `lifecycle_status=ARCHIVED` + motivo | Oculto (filtro Arquivados) | Bloqueado | Sim → Restaurar |
| **Anular** | `is_active=false` + motivo | Oculto (filtro Anulados) | Impossível | Não (histórico preservado) |

\* Produto descontinuado pode entrar em ordem apenas com `discontinued_override_reason` na API de itens (`POST /api/importations/{id}/items`).

**Combobox Nova Ordem:** `GET /api/products?for_combobox=true` → só produtos `ACTIVE` (exclui descontinuados, arquivados e anulados).

### Import Heroes na Central da ordem (L-UX-001)

Ordens criadas via **Nova Ordem** com planilha Heroes vinculada exibem o painel **Planilha Heroes** na Central (`HeroesImportPanel`):

1. **Preview** — parser no run `ATTACHED` da ordem (não use `/imports/heroes/xlsx/preview` no mesmo arquivo — retorna 409).
2. **SKUs** — racchettas com grafias equivalentes (`show`, `show 26`, `show26`) são **agrupadas** por chave canônica (base + ano; sem ano → ano corrente). Ao vincular na `/revisao`, marque **Salvar grafias no produto** para persistir o de-para em `commercial_notes` (`HEROES_ALIASES:`).
3. **Commit** — bloqueado enquanto houver grupo pendente; após vincular uma vez por grupo, merge cria faturas/pagamentos/itens na ordem manual existente.

Cadastre `description` alinhada ao nome Heroes (ex.: `SHOW 2026`, `AURA`) para maximizar sugestões automáticas na fila.

---

## 9. Endpoints REST (resumo)

Prefixo: `/api/products`  
Permissões: leitura `importation:read`; escrita `importation:write`.

| Método | Rota | Uso principal |
|---|---|---|
| GET | `/catalog` | Lista enriquecida da tela principal |
| GET | `/export?format=csv\|xlsx` | Export server-side |
| POST | `/import/preview` | Preview importação |
| POST | `/import/commit` | Grava importação |
| POST | `/bulk/archive` | Arquivar em massa |
| POST | `/bulk/restore` | Restaurar em massa |
| POST | `/bulk/status` | Descontinuar/reativar em massa |
| POST | `/bulk/cancel` | Anular em massa |
| GET | `/?for_combobox=true` | Lista para Nova Ordem |
| GET | `/` | Lista simples (legado) |
| POST | `/` | Criar produto |
| GET | `/{id}/detail` | Detalhe enriquecido |
| GET | `/{id}/readiness?context=` | Validação por etapa |
| GET | `/{id}/audit` | Histórico |
| GET | `/{id}/orders` | Ordens vinculadas |
| GET | `/{id}/cost-history` | Histórico LC |
| POST | `/{id}/archive` | Arquivar um |
| POST | `/{id}/restore` | Restaurar um |
| POST | `/{id}/cancel` | Anular um |
| GET | `/{id}` | Produto básico |
| PATCH | `/{id}` | Atualizar campos |

---

## 10. Validações de uso em importações

**Arquivo:** `app/api/importations.py` → `_validate_item_product()`  
**Serviço:** `validate_product_for_usage()` em `product_catalog.py`

Ao adicionar item com `product_id` em ordem:

| Situação | Resultado |
|---|---|
| Produto anulado | HTTP 422 |
| Produto arquivado | HTTP 422 |
| Produto descontinuado sem override | HTTP 422 |
| Produto descontinuado + `discontinued_override_reason` (≥3 chars) | Permitido |
| Campos incompletos para contexto `importation` | HTTP 422 (ex.: sem `product_group`) |

Contextos de readiness também existem para `customs` e `landed_cost` (endpoint `/readiness`; integração parcial em outras fases).

---

## 11. Fluxo visual resumido

```
/cadastros/produtos (ProductsPage)
  │
  ├─ Clique na linha ──► ProductQuickDrawer ──► PATCH ou POST /api/products
  │
  ├─ Clique no SKU ──► /cadastros/produtos/:id (ProductDetailPage)
  │                      └─ 5 abas ──► PATCH / detail / orders / audit / documents
  │
  ├─ Seleção + bulk ──► POST /api/products/bulk/*
  │
  └─ Importar ──► POST /import/preview + /import/commit
```

---

## 12. Testes relacionados

| Teste | Cobertura |
|---|---|
| `tests/test_product_catalog.py` | API catalog, archive, NCM, bulk, import, export |
| `frontend/src/pages/products/productCatalogUtils.test.ts` | Labels, elegibilidade bulk, sort |

---

*Última atualização: cadastro mestre reintegrado (migração 011 + API catalog + UI híbrida).*
