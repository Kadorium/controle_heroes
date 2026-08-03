# Document Readiness — A1 Logistics + A2 Orders/Billing

| Campo | Valor |
|---|---|
| Status A1 | **DONE** (capacidade) |
| Status A2 | **DONE** (capacidade) |
| Status DR-UX | **DONE** (fechamento + patch corretivo H-FIX) |
| Aceite visual Logistics | **ACCEPTED_WITH_MINOR_BACKLOG** (sem colapso de densidade P2) |
| Aceite visual Orders/Billing | **ACCEPTED** |
| Document Readiness | **concluído** (capacidade + aceite UI operacional) |
| Data | 2026-08-03 |
| Roadmap | 0.5.54 |
| Blueprint | 0.2.14 |
| Alembic | `010_order_invoice_item_unit` (sem migration DR-UX) |
| Escopo | A1+A2 capacidade + DR-UX UI — sem J#5/J#3/fiscal |

---

# A1 — J4-UX2 Logistics (resumo)

Ver seção histórica abaixo e evidências em [`screenshots/`](screenshots/) (`a1-*`).

| Campo | Valor |
|---|---|
| Status A1 | **DONE** |
| Alembic | `009_package_content_snapshots` |

## Preflight A1 (antes de A2)

| Check | Resultado |
|---|---|
| Abrir Shipment pela UI | OK |
| Criar package completo | OK |
| Intervalo em lote | OK |
| Editar contents | OK |
| Registrar DocumentSummary | OK |
| Upload documento | OK |
| `FATTURA_DOGANALE` só como provenance de snapshot | OK |
| **Veredito preflight** | **PASS** |

Sem regressão material A1 observada; nenhuma correção A1 embutida em A2.

---

# DR-UX — Fechamento operacional UI (pós A1/A2)

| Campo | Valor |
|---|---|
| Status | **DONE** (após patch corretivo H-FIX 2026-08-03) |
| Capacidade A1/A2 | permanece **DONE** (não reabre J#4) |
| Aceite operacional A1 | **fechado** |
| Data | 2026-08-03 |
| Suite | `npm run e2e:dr-ux` |
| Roadmap | 0.5.54 |

## Hipóteses do patch corretivo (H-FIX)

| ID | Veredito | Correção |
|---|---|---|
| H-FIX-1 qty wire | **CONFIRMADA** em ShipmentItem/contents (`10.0000`); Invoice load já compactava, mas `saveItems` reintroduzia wire | `compactQuantityWire` em ShipmentItem, contents reload, `saveItems`; E2E assert `qty-0=10`, `qty-1=2` |
| H-FIX-2 Provenance | **CONFIRMADA** (coluna tabela) | Header → `Origem do total declarado`; pesos com `formatQuantity` |
| H-FIX-3 Invoice layout 1366 | **CONFIRMADA** (colunas à direita cortadas) | CSS `.invoice-items-table` + `density=finance` |
| H-FIX-4 download | **CONFIRMADA** (cobertura incompleta) | pytest MIME/CD/404 arquivo/traversal/sem Audit; E2E bytes PDF |
| H-FIX-5 gates | **CONFIRMADA** (só comandos) | Tabela de resultados abaixo |
| H-FIX-6 screenshots | **CONFIRMADA** (imagens contradiziam DONE) | Regeneradas `drux-invoice-header`, `drux-a1-contents-reload`, `drux-a1-summary-reload`, `drux-doc-download` |

## Entregas

| Área | Mudança |
|---|---|
| Orders | `supplier_name` / `supplier_is_active` via `catalog.public`; cancel default vazio + max 64; `DocumentActions` |
| Billing | Cabeçalho `invoice-header`; qty compacta após load/save; tabela itens 1366; `DocumentActions` |
| Documents | `GET /api/documents/{id}/content` (FileResponse; auth entity-linked; sem Audit GET) |
| Logistics | Microcopy PT; FormFields; `source_line_reference`; summary sem “Provenance”; qty compacta; `DocumentActions` |
| Evidência | Screenshots `drux-*` 1366 regeneradas no patch |

## Screenshots DR-UX

| Arquivo | Conteúdo |
|---|---|
| `screenshots/drux-order-supplier.png` | Fornecedor enriquecido no pedido |
| `screenshots/drux-doc-download.png` | Abrir/Baixar documento Order |
| `screenshots/drux-invoice-header.png` | Invoice DRAFT qty `10`/`2` + tabela legível 1366 |
| `screenshots/drux-a1-package.png` | Editor de volumes |
| `screenshots/drux-a1-batch.png` | Intervalo em lote |
| `screenshots/drux-a1-contents-filled.png` | Contents com `source_line_reference` |
| `screenshots/drux-a1-contents-reload.png` | Contents após reload (qty compacta) |
| `screenshots/drux-a1-summary-reload.png` | Summary “Origem do total declarado” + totais |

Históricos `a1-*` / `a2-*` preservados.

## Minor backlog (não bloqueia)

- Densidade colapsável (`<details>`) na mesma rota de Shipment (P2).
- Microcopy “scadenze” em blockers de Invoice (legado Billing; fora do patch DR-UX).

## Resultados dos gates (observados 2026-08-03)

| Gate | Comando | Resultado | Contagem | Duração | Evidência |
|---|---|---|---|---|---|
| pytest DR-UX | `pytest tests/test_drux_documents_orders.py -q` | **PASS** | 7 passed | ~4.1s | download 200/403/404/traversal; sem Audit GET |
| architecture | `pytest tests/architecture/test_import_boundaries.py -q` (com DR-UX) | **PASS** | 11 passed total | ~11.3s | boundaries OK |
| Vitest | `vitest run src/ui src/features/orders src/features/billing src/features/shipments` | **PASS** | 49 passed / 11 files | ~3.0s | format/DocumentActions/contents |
| TypeScript | `npx tsc --noEmit` | **PASS** | 0 errors | incluso no build | — |
| build | `npm run build` | **PASS** | vite OK | ~1.0s | `dist/` |
| OpenAPI drift | `npm run check:api-drift` | **PASS** | up to date | <1s | generated client |
| E2E DR-UX | `npm run e2e:dr-ux` | **PASS** | 1 passed | ~8.9s playwright / ~19s suite | screenshots `drux-*` |
| E2E A2 | `npm run e2e:a2` | **PASS** | 1 passed | ~6.5s / ~17s suite | regressão Orders/Billing |
| E2E Logistics | `npm run e2e:logistics` | **PASS** | 4 passed | ~6.7s / ~17s suite | assert batch CTNS escopado |

## Handoff

Próxima ação canônica: **planejar J#5** (Customs + Inventory). A1/A2 capacidade **DONE**; DR-UX aceite operacional **DONE**.

---

# A2 — Orders/Billing Document Readiness

## Estado inicial

- A1 DONE; head Alembic `009`.
- `Order.order_date` / `Order.notes` / `Invoice.invoice_date` existiam no BE; UI create/edit omissa ou parcial.
- `OrderItem.unit` / `InvoiceItem.unit` **não** existiam.
- Upload Invoice OK; upload Order só via API Documents (`entity_type=order`), sem UI.
- Sem domínio fiscal N3.1 / ART 8.

## Hipóteses

| ID | Hipótese | Veredito |
|---|---|---|
| H-A2-1 | `order_date` no BE; falta exposição create/edit UI | **PARTIAL** → BE confirmado (Date NOT NULL, ISO `YYYY-MM-DD`, sem timezone); UI create/edit/detail/listagem pt-BR fechada em A2 |
| H-A2-2 | `invoice_date` no BE; falta create/edit | **PARTIAL** → create/edit DRAFT + detail pt-BR; imutável após ISSUED |
| H-A2-3 | Adicionar `unit` opcional em OrderItem | **CONFIRMADA** (campo inexistia) → String(16) nullable, normalizado UPPER |
| H-A2-4 | Adicionar `unit` em InvoiceItem + herança | **CONFIRMADA** → copia do OrderItem no create; omitido no replace herda; chave `unit` = override explícito; ISSUED imutável |
| H-A2-5 | Expor `Order.notes` na UI | **PARTIAL** → BE Text nullable; create/edit/detail; vazio→null; audit `update_header` |
| H-A2-6 | Documentos `entity_type=order` | **PARTIAL** → API Documents já OK; UI upload/listagem no detalhe; sem infra nova |
| H-A2-7 | Billing docs sem redesenho | **CONFIRMADA** — upload Invoice preservado; E2E issue OK |
| H-A2-8 | Migration após `009` | **CONFIRMADA** → `010_order_invoice_item_unit` |
| H-A2-9 | Contrato APIs para J#3 | **CONFIRMADA** após A2 (datas, notes, unit, DocumentLink order/invoice) |
| H-A2-10 | Escopo fiscal fora | **CONFIRMADA** — sem campos N3.1/ART8/imponibile |

## Migration

- `v2/alembic/versions/010_order_invoice_item_unit.py`
- Revises: `009`
- Colunas: `order_items.unit` VARCHAR(16) NULL; `invoice_items.unit` VARCHAR(16) NULL
- Sem backfill; sem índice (baixa cardinalidade / filtro não previsto)
- Upgrade/downgrade: add/drop columns

## Campos

| Campo | Tipo | Nulo | UI | API |
|---|---|---|---|---|
| `Order.order_date` | date | NOT NULL (default today) | create/edit/detail; pt-BR | create/PATCH |
| `Order.notes` | text | NULL | create/edit/detail | create/PATCH; `""`→null |
| `OrderItem.unit` | String(16) | NULL | create/edit(blur)/detail | add/update item |
| `Invoice.invoice_date` | date | NULL | create/edit DRAFT/detail | create/PATCH |
| `InvoiceItem.unit` | String(16) | NULL | detail + replace | create herda; replace herda/override |

## Regra de unidade

1. Snapshot documental opcional (PZ, SET, CTNS, UN, …) — **não** módulo UoM.
2. Normalização: trim + UPPER; max 16; vazio→null.
3. Create Invoice: copia `OrderItem.unit` → `InvoiceItem.unit`.
4. `replace_items`: se `"unit" in payload` → override (incl. null explícito); senão herda do OrderItem atual.
5. Após ISSUED: itens/header imutáveis (`_require_draft`).
6. Billing **não** importa internals de Orders (`normalize_unit` espelhado em `billing.money`).

## Documentos Order

- Reuso `POST /api/documents` com `entity_type=order`.
- UI: listagem + `FileUpload` em `OrderDetailPage`.
- Invoice upload inalterado.
- RBAC/Audit: contrato Documents existente; Order audit `create` / `update_header` / `update_item` / `add_item`.

## Alterações backend

- Models Orders/Billing + migration 010
- `normalize_unit` em `orders.money` e espelho em `billing.money`
- Commands/routes/schemas/OpenAPI: unit em itens; header dates/notes
- Invoice create copia unit; replace herda/override

## Alterações frontend/UI

- `OrderCreatePage`: order_date, notes, line unit
- `OrderDetailPage`: header edit, notes, unit edit DRAFT, documentos
- `OrderInvoicesPanel`: invoice_date no create
- `InvoiceDetailPage`: edit date DRAFT, coluna Un., hint herança, replace envia unit
- OpenAPI regenerado; suite `npm run e2e:a2`

## Screenshots

| Arquivo | Conteúdo |
|---|---|
| `screenshots/a2-order-create.png` | Create com data/notes/unidades |
| `screenshots/a2-order-detail-docs.png` | Detalhe + documento Order |
| `screenshots/a2-invoice-before-issue.png` | Invoice DRAFT com units/date |
| `screenshots/a2-invoice-issued.png` | Persistência pós-emissão |

## Testes

```text
cd v2
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m pytest tests/test_orders_billing_a2.py tests/architecture/test_import_boundaries.py -q
cd frontend
npm run generate:api
npm run check:api-drift
npx vitest run src/features/orders src/features/billing
npx tsc --noEmit
npm run build
npm run e2e:a2
```

## Matriz de contrato (itens A2)

Status pós-A2 (ex-`READY_BACKEND_UI_PENDING`):

| Documento | Campo | Owner | Status |
|---|---|---|---|
| Ordine | Del / order_date | Orders | **READY_FOR_MANUAL_ENTRY** |
| Ordine | UM / OrderItem.unit | Orders | **READY_FOR_MANUAL_ENTRY** |
| Ordine | Note | Orders | **READY_FOR_MANUAL_ENTRY** |
| Ordine | Arquivo DocumentLink | Documents→Order | **READY_FOR_MANUAL_ENTRY** |
| Ordine | Iva N3.1 / totais IVA | Fiscal/PDF | **DOCUMENT_ONLY** (fora A2) |
| Fattura | Del / invoice_date | Billing | **READY_FOR_MANUAL_ENTRY** |
| Fattura | UM / InvoiceItem.unit | Billing | **READY_FOR_MANUAL_ENTRY** |
| Fattura | Arquivo oficial | Documents→Invoice | **READY_FOR_MANUAL_ENTRY** (sem regressão) |
| Endereços/PI/CF/REA/IBAN | PDF | Documents | **DOCUMENT_ONLY** |

Itens Logistics A1: ver plano / seção A1 — readiness de volumes permanece.

## Gaps residuais

- N3.1 / ART 8 / imponibile → PDF ou domínio fiscal futuro (não Orders/Billing genérico).
- Customs/Inventory/Numerário → J#5.
- Ingestão/parser/staging → J#3 (via public APIs agora habilitadas).
- Costing → J#6.
- Sem transcrição integral dos PDFs.

## Handoff J#5

ImportProcess/DUIMP, Doganale canônico, Numerário, multi-invoice, origem/fabricante, impostos — **não** forçar em Orders/Billing/Logistics snapshots.

## Handoff J#3

Adapters podem, via APIs públicas:

- criar Order com `order_date` + `notes`;
- OrderItems com `unit`;
- vincular Document a `entity_type=order`;
- criar Invoice com `invoice_date`;
- InvoiceItems com `unit` (herança/override);
- preservar snapshots sem acessar internals.

Pipeline: arquivo→hash→tipo→extração→staging→revisão→commit idempotente→provenance.

---

# A1 — detalhe (histórico)

## Estado inicial (A1)

- J#4 DONE; J4-UX1 DONE; head Alembic `008`.
- Backend package/contents/summary existiam; UI só type/count/parent; summaries read-only; upload Shipment ausente.
- PackageContent sem snapshots de linha PL; sem batch atômico.

## Hipóteses (A1)

| Hipótese | Veredito |
|---|---|
| Backend já tinha campos físicos de package | **CONFIRMADA** |
| Faltavam snapshots de linha PL sem colapsar pesos | **CONFIRMADA** → Alt A em PackageContent |
| UI era API_ONLY para fatos Logistics necessários | **CONFIRMADA** → fechado em A1 |
| Doganale pode ir em DocumentSummary com provenance | **CONFIRMADA** — snapshot, não SoT Customs |
| Parser/OCR necessário para A1 | **REFUTADA** — fora de escopo |

## Alterações backend (A1)

- Migration `009`: colunas PackageContent + `declared_provenance` em DocumentSummary.
- Commands: `set_package_contents` ampliado; `add_shipment_packages_batch`; `update_shipment_packages_batch`; provenance em upsert summary.
- HTTP: `POST/PATCH /api/shipments/{id}/packages/batch`; schemas Content/Summary atualizados.
- Public API exporta batch.

## Alterações frontend/UI (A1)

- [`ShipmentLogisticsPanels.tsx`](../../../v2/frontend/src/features/shipments/ShipmentLogisticsPanels.tsx)
- [`ShipmentDetailPage.tsx`](../../../v2/frontend/src/features/shipments/ShipmentDetailPage.tsx)
- [`shipmentsApi.ts`](../../../v2/frontend/src/features/shipments/shipmentsApi.ts)
- OpenAPI regenerado.

## Campos PackageContent (A1)

`source_ncm`, `source_description`, `units_per_package`, `unit_net_weight_kg`, `unit_gross_weight_kg`, `source_total_net_weight_kg`, `source_total_gross_weight_kg`.

DocumentSummary: `declared_provenance` ∈ PACKING_LIST | FATTURA_DOGANALE | MANUAL | OTHER.

## Arquivos centrais A2

- `v2/alembic/versions/010_order_invoice_item_unit.py`
- `v2/app/orders/{models,commands,routes,money}.py`
- `v2/app/billing/{models,commands,routes,money}.py`
- `v2/tests/test_orders_billing_a2.py`
- `v2/frontend/src/features/orders/{OrderCreatePage,OrderDetailPage,ordersApi}.*`
- `v2/frontend/src/features/billing/{InvoiceDetailPage,billingApi}.*`
- `v2/frontend/e2e/a2-orders-billing-readiness.spec.ts`
