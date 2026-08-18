# MDM-UX — Plano mestre (espelho)

Espelho de decisão: [`MDM_UX_ADVISOR_HANDOFF.md`](MDM_UX_ADVISOR_HANDOFF.md).  
**Este é o mestre da fase.** Campanha **fechada**. Não criar `.plan` concorrente. Não relançar MDM-1…CF.

| Campo | Valor |
|---|---|
| Campanha | MDM-UX — cadastros mestres e qualidade de dados |
| Status | **DONE / ENCERRADA** |
| Roadmap | **0.5.125** — B.1 = pagar numerário; MDM-UX DONE |
| Blueprint | **0.2.25** |
| Alembic | **026** (L-006 + `Supplier.tax_id`) |
| Lane | Walk: `:8082` / `epic_v2_test` / cookie `epic_v2_test_session` |
| Operação | `:8081` / `epic_v2` — schema 026 nullable; 589 e TESTE-CICLO-001 intocados |

Não misturar com settlement CUSTOMS_FUNDING, J#5-REC, J#6, RUX-3A/020, B0, ProductFamily.

## DECs (ratificadas)

- **FLAT** — Product = SKU; sem família/variante/parent.
- **NAV** — Menu **não** é grupo “Cadastros”. Produtos (`catalog:read`): Produtos + Fornecedores. Administração só com `users:read`: Usuários (esconder, não 403). Prestadores permanecem em Logística.
- **MIN-CREATE** — Product: sku + description. Supplier: name.
- **MATCH-SKU** — Ingestion continua por `Product.sku`. I.V.* = COMMITMENT.
- **LIST-CONTRACT** — `GET /api/products` e `/api/suppliers` permanecem **array**. List Report: `GET /api/catalog/product-list` e `supplier-list` com `{items,total,limit,offset}`. Sem `oneOf`.
- **NO-020** — 020 / refs / sequence / RUX-3A fora.
- **SUPPLIER-TAX-ID** — `tax_id` na 026; opcional; unique parcial `(country_code, tax_id)`; dígitos; IT strip `IT`.
- **INCOMPLETE-P1** — filtro `ncm IS NULL OR ean IS NULL`; não bloqueia processo. CAP-006 permanece não implementado.
- **USER-SECURITY** — `users:read/write`; senha definida pelo admin; sem e-mail/token; sem editor de `permissions_json`; self-deactivate proibido; último admin ativo protegido; audit na mesma UoW; HTTP via Foundation.
- **CSV** — **FUTURO**. Não nesta campanha.
- **L-006** — **PARTIAL**.

## Fatias

```
MDM-1 API → MDM-2 List+nav+pickers → MDM-3 object pages
  → MDM-4 026+qualidade → MDM-5 Users UI + Prestadores no rail Logística
  → MDM-CF
```

## Normalização

`normalize_unit` e strip NCM/EAN/tax_id vivem em `app/catalog/normalization.py`. Catalog **não** importa Orders (ADR-14).

## Progresso

| Fatia | Estado |
|---|---|
| MDM-1 | **DONE** — PATCH Product/Supplier; list-report envelope; User CRUD via Foundation; OpenAPI |
| MDM-2 | **DONE** — rail Produtos + Administração condicional; pickers `q`; createSku exige descrição |
| MDM-3 | **DONE** — fichas Product/Supplier (campos atuais + L-006/`tax_id` na UI) |
| MDM-4 | **DONE** — Alembic **026** em `epic_v2`; modelos L-006 + `tax_id`; NCM 8 dígitos; size/color distinct |
| MDM-5 | **DONE** — UI Usuários; Prestadores no rail Logística; `GET /api/logistics-providers?q=` |
| MDM-CF | **DONE** — pytest 574; rebuild `epic_v2_test`; massa 61; walk 5174 |

`epic_v2` recebeu só schema nullable 026; pedidos 589 / TESTE-CICLO-001 intocados.
