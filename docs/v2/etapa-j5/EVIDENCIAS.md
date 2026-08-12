# Etapa J#5 — Evidências

| Campo | Valor |
|---|---|
| Fase | Aduana + Inventory (J#5) |
| Status | **DONE** (core + patch fechamento) |
| Último checkpoint | **Patch C0…C5 DONE** (2026-08-04) |
| Blueprint | **0.2.16** |
| Roadmap | **0.5.63** |
| Alembic head | `015_nationalization_inventory` |
| Aceite UI | **ACCEPTED_WITH_BACKLOG** — [`UI_ACCEPTANCE_J5.md`](UI_ACCEPTANCE_J5.md) |
| Relatório | [`J5_EXECUTION_REPORT.md`](J5_EXECUTION_REPORT.md) |
| DEC Alt. B | [`patch-close/DEC_ALT_B_CUSTOMS_PAYMENT.md`](patch-close/DEC_ALT_B_CUSTOMS_PAYMENT.md) |

## Patch fechamento (2026-08-04)

| Item | Evidência |
|---|---|
| KPIs multi-moeda + drawer Customs | `j5-10-customs-payable-ap.png`; pytest `test_ap_queue_kpis_never_mix_currencies` |
| SC-10 conservação (RECLASS) | `j5-13-sku-position.png`; `j5-14-inventory-movements.png`; e2e asserts bonded=3 / available=2 / cleared=0 |
| Isolamento Treasury | notice `ap-customs-settlement-notice`; elegíveis excluem CUSTOMS_FUNDING |
| Boundaries | `test_billing_reporting_do_not_depend_on_customs`; GET `/api/customs/funding-requests/{id}` |
| Logs | `logs/patch-close-pytest.txt`, `logs/patch-close-pytest-full.txt`, `logs/patch-close-e2e-j5.txt` |

## Sequência de migrations (fechada em I5-1)

| Rev | Conteúdo | Quando |
|---|---|---|
| 011 | `import_processes`, joins invoice/shipment, item allocations | I5-1 |
| 012 | Doganale / versions | I5-2 |
| 013 | FundingRequest / Payee / tax-expense lines | I5-3A |
| 014 | Payables Customs / FundingPayableLink (Billing) | I5-3B |
| 015 | Inventory locations/movements | I5-4 |

Migrations anteriores são imutáveis; não criar tabelas futuras vazias.

---

## I5-0 — scaffold (histórico)

Gates: arch + `test_j5_i5_0_scaffold` — PASS. Ver secção anterior / log `i5-0-pytest.txt`.

---

## I5-1 — ImportProcess, vínculos e alocações

### Hipóteses

| ID | Veredito |
|---|---|
| H-I51-1 ImportProcess | **CONFIRMADA** |
| H-I51-2 Invoice links + item alloc | **CONFIRMADA** (qty only; amount/currency não necessários) |
| H-I51-3 Shipment links + item alloc | **CONFIRMADA** (DEC-DUIMP-MULTI-SHIP) |
| H-I51-4 Lifecycle DRAFT/SUBMITTED/CANCELLED | **CONFIRMADA** (sem CLEARANCE+) |
| H-I51-5 Documents | **CONFIRMADA** (`entity_type=import_process`) |
| H-I51-6 Public API I5-1 | **CONFIRMADA** (stubs futuros removidos da superfície) |
| H-I51-7 RBAC | **CONFIRMADA** — papel operacional Customs **adiado a I5-5**; admin write + comprador read |
| H-I51-8 UI mínima | **CONFIRMADA** |
| H-I51-9 SkuPosition | **NOT_APPLICABLE** em I5-1 — decisão I5-4: Inventory→Logistics ok; sem Orders; `future_order_qty` via Reporting |

### Modelo

- `ImportProcess` (code imutável `IMP-…`, external_reference, status, version, notes, submitted_at, cancelled_at, cancel_reason)
- `import_process_invoices` (`invoice_id` UNIQUE; só ISSUED)
- `import_process_invoice_items` (allocated_qty; residual ≤ invoice item qty)
- `import_process_shipments` (`shipment_id` UNIQUE)
- `import_process_shipment_items` (allocated_qty; Σ ≤ shipped qty)

### Lifecycle

- DRAFT → SUBMITTED (exige external_reference + ≥1 invoice)
- DRAFT|SUBMITTED → CANCELLED (reason obrigatório)
- Estrutura mutável só em DRAFT; optimistic lock 409

### APIs públicas / HTTP

`customs.public` + `/api/import-processes/*` (create/get/list/update, link/unlink, allocate, submit/cancel, residuals).

### UI

`/customs`, `/customs/new`, `/customs/:id` — SCR-019/022 mínimo; placeholders Doganale/Numerário/Inventory.

### Gates

| Gate | Resultado |
|---|---|
| Migration 011 up → down 010 → up | **PASS** |
| pytest `test_customs_i5_1` + arch | **PASS** (13) |
| Vitest customs | **PASS** (2) |
| `tsc --noEmit` + build | **PASS** |
| `npm run e2e:j5-i5-1` | **PASS** (1) |
| Screenshots 1366 | `screenshots/i5-1-*-1366.png` |

### Comandos

```bat
cd v2
.venv\Scripts\python.exe -m pytest tests/test_customs_i5_1.py tests/architecture/test_import_boundaries.py -q

cd v2\frontend
npm test -- --run src/features/customs
npm run build
npm run e2e:j5-i5-1
```

### Logs

- [`logs/i5-1-pytest.txt`](logs/i5-1-pytest.txt)
- [`logs/i5-1-e2e.txt`](logs/i5-1-e2e.txt)

### Gaps / handoff I5-2

- Sem Doganale / Numerário / Nationalization / Inventory
- Sem papel RBAC “despachante” dedicado (I5-5)
- SkuPosition/`future_order_qty` a fechar antes de I5-4
- Próximo: **I5-2** Doganale versionada + UI aba + divergências

---

## I5-3A — Numerário (FundingRequest + Payee)

### Escopo entregue

- Migration **013** (`customs_payees`, `customs_funding_requests`, value/tax/expense lines)
- Payee **sem** Supplier FK
- FundingRequest status `DRAFT|CONFIRMED|CANCELLED`; version lock; idempotency per process
- Linhas com `amount` nullable (`vazio ≠ 0`); `structured_total` / `divergence` vs `declared_total`
- `confirm` **não** cria Payable (I5-3B)
- HTTP: `/api/customs/payees`, `/api/import-processes/{id}/funding-requests/*`
- UI: `NumerarioPanel` em `CustomsDetailPage`

### Gates

| Gate | Resultado |
|---|---|
| pytest `test_customs_i5_3a` + scaffold + arch | **PASS** (17) |
| `npm run generate:api` + `check:api-drift` | **PASS** |
| `npx tsc --noEmit` | **PASS** |

### Logs

- [`logs/i5-3a-pytest.txt`](logs/i5-3a-pytest.txt)

### Gaps / handoff I5-3B

- Sem Payable / FundingPayableLink / AP origem Customs
- Sem e2e:j5-i5-3a dedicado (pytest + UI mínima)
- Lifecycle Blueprint (ISSUED / PARTIALLY_SETTLED / SETTLED) permanece para I5-3B+
- Próximo: **I5-3B** Payable extension + regressão Inc-6/AP

---

## I5-3B — Payables Customs (FundingPayableLink)

### Escopo entregue

- Migration **014**: `payables.invoice_id`/`payment_term_id` nullable; `source_type`/`source_id`/`payee_display_name`; partial UNIQUE `(invoice_id, sequence)`; UNIQUE `(source_type, source_id, sequence)`; tabela `funding_payable_links`
- `billing.public.create_customs_payable_from_funding` / `cancel_customs_payable`
- `confirm_funding_request` cria Payable agrupado (seq=1) + link; idempotente; cancel CONFIRMED se Payable OPEN sem liquidação
- AP/`payables_queue`: outerjoin Invoice; denormaliza `payee_display_name` (Reporting **sem** edge Customs)
- **Confirmado:** Treasury não redesenhado — customs payables **não** elegíveis em `list_eligible_payables` (INNER JOIN Invoice); alocação Payment bloqueia `invoice_id is None`
- UI: NumerarioPanel mostra Payable + link AP; AP badge Numerário

### Gates

| Gate | Resultado |
|---|---|
| pytest billing/treasury/reporting + i5_3a/i5_3b + arch | **PASS** (49) |
| `npm run generate:api` + `tsc --noEmit` | **PASS** |

### Logs

- [`logs/i5-3b-pytest.txt`](logs/i5-3b-pytest.txt)

### Gaps / handoff I5-4

- Sem Payment/Allocation para origem Customs (gap intencional até decisão futura)
- Lifecycle Blueprint ISSUED/PARTIALLY_SETTLED/SETTLED ainda aberto
- Próximo: **I5-4** Nationalization + Inventory (migration 015)

---

## I5-4 — Nationalization + Inventory + SkuPosition

### Escopo entregue

- Migration **015** (revises 014): `nationalizations` / `nationalization_items`; `stock_locations` / `goods_receipts` / `goods_receipt_lines` / `inventory_movements` / `stock_balances`; seed BONDED-MAIN / DOMESTIC-MAIN / QUARANTINE-MAIN; check `import_processes.status` expandido
- Customs: `create_nationalization` / `add_items` / `confirm` / `reverse` / `nationalize`; anti-oversubscription 409; status processo → PARTIALLY_CLEARED / CLEARED
- Inventory: receipt bonded pré-nac; domestic exige nat; movimentos append-only; StockBalance derivado + rebuild; SkuPosition (buckets; `future_order_qty=null` deferred)
- HTTP: nationalization sob `/api/import-processes/...`; inventory `/api/inventory/...`
- UI: NationalizationPanel + ReceiptPanel em CustomsDetail; `/inventory/sku/:productId` + `/inventory/movements`; nav Estoque

### Decisões

| Tema | Decisão |
|---|---|
| ImportProcess status | +`IN_CLEARANCE`, `PARTIALLY_CLEARED`, `CLEARED` (mantém DRAFT/SUBMITTED/CANCELLED); CLOSED não neste incremento |
| Ownership | Nationalization = Customs; Inventory lê via `customs.public` (sem aresta customs→inventory — evita ciclo) |
| SkuPosition | Query composta; `in_transit_qty` best-effort (ShipmentItem sem product_id; Inventory ↛ Orders); `future_order_qty` omitido/null |
| ARRIVED | Não cria stock |

### Gates

| Gate | Resultado |
|---|---|
| `pytest tests/test_inventory_i5_4.py tests/test_customs_i5_3b.py tests/architecture` | **PASS** |
| scaffold I5-0 atualizado (nationalize + inventory implemented) | **PASS** |
| `npm run generate:api` + `tsc --noEmit` | **PASS** |

### Logs

- [`logs/i5-4-pytest.txt`](logs/i5-4-pytest.txt)

### Gaps / handoff I5-5

- `in_transit_qty` por product permanece aproximado até Logistics expor product no item público ou Reporting
- UX transversal SCR-019/022/024/025 (I5-5)
- E2E j5 + screenshots (I5-6)

---

## I5-5 — UX transversal SCR-019/022/024/025

### Escopo entregue

- **SCR-019** `CustomsListPage`: breadcrumbs; KPIs; filtros de status (incl. liberação); paginação-resumo; empty/loading/error/forbidden; StatusBadge
- **SCR-022** `CustomsDetailPage`: seções Resumo / Faturas / Alocações / Embarques / Documentos / Doganale / Numerário / Liberações / Recebimentos / Auditoria; DocumentActions + FileUpload; 409/`conflictMessage`; labels pt-BR
- **SCR-024** `SkuPositionPage`: buckets com labels persistentes; empty; formatQuantity
- **SCR-025** `MovementsPage`: filtro por produto; tabela; labels de movimento; PaginationSummary; empty/forbidden
- Painéis: títulos sem schema interno (`FundingRequest`/`Nationalization`/`GoodsReceipt` → Numerário/Liberações/Recebimentos)
- Papéis seed Identity (sem migration): `aduana`, `estoque` (idempotentes via `ensure_*_role` no bootstrap admin)
- Sem mudança de contratos de domínio; head Alembic permanece **015**

### Papéis / permissões

| Role | Permissões |
|---|---|
| `aduana` | `customs:read`, `customs:write`, `customs:clear`, `documents:read`, `documents:write`, `audit:read` |
| `estoque` | `inventory:read`, `inventory:write`, `inventory:adjust`, `documents:read`, `audit:read` |

Admin inalterado (continua com matriz completa). Comprador permanece read-only em customs/inventory.

### Gates

| Gate | Resultado |
|---|---|
| pytest `test_j5_i5_5_roles` + scaffold | **PASS** |
| Vitest customs + inventory labels/permissions | **PASS** |
| `npx tsc --noEmit` + build | **PASS** |
| `npm run e2e:j5-i5-5` (smoke list/detail/estoque) | **PASS** |

### Logs

- [`logs/i5-5-pytest.txt`](logs/i5-5-pytest.txt)

### Gaps / handoff I5-6

- Campanha E2E completa + screenshots 1366 + aceite SC-07/09/10 — **concluída em I5-6**
- Sem usuário seed dedicado aduana/estoque (só role; login E2E futuro sob demanda) — minor backlog
- Próximo (histórico): **I5-6**

---

## I5-6 — E2E + aceite final J#5

### Escopo entregue

- Suite `e2e:j5` (`e2e/suites/j5.txt`): i5-1 + i5-2 + i5-5 + `j5-acceptance.spec.ts`
- 15 screenshots 1366 fullPage em `screenshots/j5-01`…`j5-15`
- Aceite SC-07 / SC-09 / SC-10; classificação **ACCEPTED_WITH_MINOR_BACKLOG**
- Fix E2E i5-1: assert SUBMITTED via `status-badge` (strict mode)
- Sem migration nova; head Alembic permanece **015**
- J#3 **não** iniciado

### Gates

| Gate | Resultado |
|---|---|
| pytest J#5 + architecture | **PASS** (51) |
| generate:api + check:api-drift | **PASS** |
| tsc + build | **PASS** |
| `npm run e2e:j5` | **PASS** (4) |
| `npm run e2e:inc-6` | **PASS** (1) |
| `npm run e2e:logistics` | **PASS** (4) |

### Logs

- [`logs/i5-6-pytest.txt`](logs/i5-6-pytest.txt)
- [`logs/i5-6-e2e-j5.txt`](logs/i5-6-e2e-j5.txt)
- [`logs/i5-6-e2e-inc6.txt`](logs/i5-6-e2e-inc6.txt)
- [`logs/i5-6-e2e-logistics.txt`](logs/i5-6-e2e-logistics.txt)

### Docs de fechamento

- [`UI_ACCEPTANCE_J5.md`](UI_ACCEPTANCE_J5.md)
- [`J5_EXECUTION_REPORT.md`](J5_EXECUTION_REPORT.md)

### Handoff

- Próxima ação Roadmap: **planejar J#3** (não executar nesta entrega)
- J#6 após J#3 na ordem do programa; L-001 permanece para Reconciliation
