# Inventário MIXED (hunks)

Arquivos que misturam MDM-UX com outras campanhas. **Não** fazer checkout de `3b10deb`. Reconstrução seletiva = hunk, não SHA.

## Nav / shell

- `v2/frontend/src/app-shell/AppShell.tsx`
  - MDM: grupo Produtos (Produtos + Fornecedores); Administração → Usuários; ícones Catalog/Users/Suppliers
  - Não-MDM: Compras, Financeiro, Logística (Embarques), Aduana, FX strip, RuntimeBadge
  - Recusado: Fornecedores no rail; Prestadores no rail
- `v2/frontend/src/app-shell/AppShell.nav.test.tsx` — asserts do rail atual (incluindo Fornecedores/Prestadores)

## Rotas

- `v2/frontend/src/App.tsx`
  - MDM additive: `/catalog/products*`, `/catalog/suppliers*`, `/admin/users*`
  - Não-MDM: orders, invoices, payables, shipments, customs, inventory, ingestion

## Pickers (KEEP — não reconstruir neste R)

- `v2/frontend/src/features/orders/OrderCreatePage.tsx` — `useCatalogSearch` + create SKU com descrição
- `v2/frontend/src/features/orders/BindProductModal.tsx` — G2
- `v2/frontend/src/features/billing/ApQueuePage.tsx` / `treasury/PaymentCreatePage.tsx` — search supplier (J4)

## Prestadores (KEEP página; REVERT rail)

- `v2/frontend/src/features/shipments/LogisticsProvidersPage.tsx`
- `v2/frontend/src/features/shipments/ShipmentsListPage.tsx` — CTA Prestadores (já existe fora do rail)
- `v2/frontend/src/features/shipments/ShipmentCreatePage.tsx` — create contextual

## Schema / testes pinados em 026

- `v2/alembic/versions/026_catalog_l006_tax_id.py` — KEEP (também empilha em 025/J4)
- Testes que pinam revisão 026 misturam J4 — não apagar ao “reverter MDM”

## OpenAPI

- Client gerado — **regen**, nunca checkout
