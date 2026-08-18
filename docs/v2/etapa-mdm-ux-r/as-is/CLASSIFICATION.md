# Classificação KEEP / REBUILD (R0)

Código de produção **não** foi alterado neste registro.

## KEEP

- Catalog models/commands/normalization/routes (PATCH, list-report, GET arrays)
- Alembic `026_catalog_l006_tax_id.py`
- Users HTTP em Foundation (`user_routes.py`)
- OpenAPI gerado (regen, nunca checkout)
- `catalogApi.ts`, `identityApi.ts`, `useCatalogSearch.ts`
- Pickers de pedido (`createSku` exige description), `BindProductModal`
- pytest `test_catalog_api.py`, `test_identity_users_api.py`
- Primitivos UI (`OperationalTable`, `FilterBar`, `PageHeader`, `StatusBadge`, …) — o **uso** nas páginas MDM falhou, não os átomos
- Rotas `/catalog/products*`, `/catalog/suppliers*`, `/admin/users*` (preservar; reconstruir páginas)

## KEEP COM AJUSTE

- AppShell chrome operacional (Compras / Financeiro / Logística / Aduana) + compact rail ≤1100 (`--shell-sidebar-rail: 56px`)
- Product Detail **seções** (Visão geral / Características / Fiscal / Físico / Auditoria)
- Product Create fluxo MIN-CREATE (SKU + descrição)
- Users em Administração (IAM-light)
- Envelope `summary` no product-list — **R3**, não agora
- SVG inline — pode ser redesenhado; sem biblioteca nova

## REBUILD (após GATE)

- `ProductListPage.tsx` / `ProductDetailPage.tsx` / `ProductCreatePage.tsx`
- `Supplier*Page.tsx` (página secundária; não rail)
- `Users*Page.tsx` (visual alinhado)
- Testes de página Vitest amarrados ao CRUD atual

## REVERT (IA — só pós-GATE no AppShell real)

- Grupo sidebar **Produtos + Fornecedores**
- **Prestadores** no rail (CTA Embarques permanece)

## Não fazer neste R0–R2

- Mutar `App.tsx` / `AppShell.tsx` / páginas reais
- Backend, schema, OpenAPI, Roadmap, Blueprint
- Escrever em `epic_v2` / `epic_v2_test`
- Rollback / delete / reset
