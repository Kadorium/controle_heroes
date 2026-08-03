# Etapa J#4 — Logistics — Evidências

| Campo | Valor |
|---|---|
| Fase | Logística (J#4) |
| Status | **DONE** |
| Data | 2026-07-31 |
| Alembic | `008_logistics_providers` (head; J#4 base `007`) |
| Blueprint | 0.2.12 |
| Roadmap | 0.5.50 |

## Gates

| Gate | Resultado |
|---|---|
| I4-0 scaffold + module_graph + orders.public `get_order_item` / `find_confirmed_order_items` | PASS |
| I4-1 alembic upgrade → downgrade 006 → upgrade head | PASS (`epic_v2_test`) |
| I4-2 pytest domínio + arch boundaries | PASS (`tests/test_logistics_api.py` + architecture) |
| I4-3 OpenAPI `generate:api` + `check:api-drift` | PASS |
| I4-4 `tsc` + vitest shipments + `npm run build` | PASS |
| I4-5 `npm run e2e:logistics` | PASS (2/2) |

## Comandos reproduzíveis

```bat
cd v2
.venv\Scripts\python.exe -m pytest tests/test_logistics_api.py tests/architecture/test_import_boundaries.py -q

cd v2\frontend
npm run check:api-drift
npm test -- --run src/features/shipments
npm run build
npm run e2e:logistics
```

## Escopo entregue

- Domínio: Shipment, ShipmentItem, ShipmentPackage, ShipmentPackageContent, ShipmentReference, ShipmentDocumentSummary
- HTTP `/api/shipments` + candidates + totais/divergences/allocation-bases
- FE `/shipments` lista/create/detail (SectionCards)
- RBAC `logistics:read` / `logistics:write`
- Divergência provisória L-001 em `app/logistics/divergence.py`

## Fora / aberto

- DEC-SHIP-CANCEL (BOOKED+) — aberto
- Importação Packing List automática — J#3
- Customs/Inventory — J#5
- Horizon B1 — não incorporado
- Upload documental completo na UI — mínimo (API pronta)
- Seed do prestador operacional real — **BLOCKED** (nome não comprovado; cadastro manual)

## Patch J4-UX1 (DONE) — 2026-07-31

| Campo | Valor |
|---|---|
| Status | **DONE** |
| Alembic | `008_logistics_providers` (head) |
| Blueprint | 0.2.12 · DEC-SHIP-PROVIDER |
| Roadmap | 0.5.50 |

### Gates

| Gate | Resultado |
|---|---|
| I4UX1-0 migration 008 + models | PASS |
| I4UX1-1 commands/public/API/RBAC + BOOKED | PASS (`test_logistics_api.py` 12) |
| I4UX1-2 OpenAPI + FE selects/providers/filtros/microcopy | PASS (`generate:api` / `check:api-drift`) |
| I4UX1-3 Vitest shipments + arch boundaries | PASS |
| E2E logistics (estendido UI create) | ver comando abaixo |

### Entregue

- `LogisticsProvider` + HTTP `/api/logistics-providers`
- Modal controlado; `logistics_provider_id` + `carrier_name_snapshot`
- BOOKED exige modal + prestador
- FE: selects create/detail; filtros lista; `/logistics-providers`; microcopy pt-BR

### Comandos

```bat
cd v2
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m pytest tests/test_logistics_api.py tests/architecture/test_import_boundaries.py -q

cd v2\frontend
npm run check:api-drift
npm test -- --run src/features/shipments
npm run e2e:logistics
```

## Próxima ação

Planejar **Aduana + Inventory (J#5)** sob pedido explícito.
