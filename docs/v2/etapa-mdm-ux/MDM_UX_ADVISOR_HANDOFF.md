# MDM-UX — retorno ao advisor (DONE)

```text
Etapa: MDM-UX — cadastros mestres e qualidade de dados (MDM-1…CF)
Status: DONE
Roadmap: 0.5.125
Blueprint: 0.2.25
Alembic: 026
Barras: inalteradas (cadeia 8/10; Aduana 2/3; Ingestão 5/7)
```

Campanha **ENCERRADA**. Não relançar MDM-1…CF. Não iniciar settlement CUSTOMS_FUNDING, J#5-REC, J#6, 020/RUX-3A nesta rodada.

Plano mestre (único): [`MDM_UX_EXECUTION_PLAN.md`](MDM_UX_EXECUTION_PLAN.md) — **fechado**.  
Runtime: [`P0_RUNTIME.md`](P0_RUNTIME.md). Vite `http://localhost:5174` → API `:8082` / `epic_v2_test` / cookie `epic_v2_test_session`. Login `admin@epic.com.br`. `epic_v2` / pedidos 589 e TESTE-CICLO-001 **intocados**.

---

## Decisão

Campanha completa **A** (MDM-1→CF) autorizada e **entregue**. Numerário volta a ser a **próxima ação** (B.1). Barras da cadeia **não sobem**.

## Estado anterior → atual

| | Antes (0.5.123 / início 0.5.124) | Depois (0.5.125) |
|---|---|---|
| Catalog HTTP | POST + GET array; sem PATCH; sem `upsert_*` | PATCH Product/Supplier; List Report envelope; GET array **preservado** |
| Product / Supplier | sku+description / name; sem L-006 / `tax_id` | Alembic **026**: L-006 + `tax_id` (PARTIAL; CAP-006 não implementado) |
| Identity HTTP | login / logout / me | CRUD usuários + senha via **Foundation**; `users:read` / `users:write` |
| Nav | Compras / Financeiro / Logística / Aduana | + **Produtos** (`catalog:read`); **Administração** só com `users:read` (esconder, nunca 403); Prestadores em Logística |
| Picker | `limit:50` sem `q` = “o catálogo” | busca `q`; SKU além dos 50 primeiros; criar SKU **exige descrição** |
| Próxima ação | MDM-UX | **pagar numerário** |

## Hipóteses — resultado

| ID | Veredito |
|---|---|
| H1 grupo único “Cadastros” | **Refutada como desenho** — DEC-NAV |
| H2 `normalize_unit` em Catalog via Orders | **Proibido** — `app/catalog/normalization.py`; Catalog ↛ Orders |
| H3 CSV nesta campanha | **FUTURO** |
| H4 size/color | Distinct + datalist; **não** fere FLAT |
| H5 L-006 = CAP-006 | **Refutada** — INCOMPLETE-P1 é filtro; CAP-006 permanece fora |
| H7 picker 50 = catálogo | **Defeito confirmado e corrigido** |

## DECs (ratificadas no Blueprint 0.2.25)

| DEC | Conteúdo |
|---|---|
| **FLAT** | Product = SKU único; sem ProductFamily / Variant / parent |
| **NAV** | Sem grupo “Cadastros”. Produtos (`catalog:read`): Produtos + Fornecedores. Administração só `users:read`. Prestadores = Logística |
| **MIN-CREATE** | Product: sku + description. Supplier: name |
| **MATCH-SKU** | Ingestion continua por `Product.sku`. I.V.* = COMMITMENT |
| **LIST-CONTRACT** | `GET /api/products` e `/api/suppliers` = **array**. List Report: `/api/catalog/product-list` e `supplier-list` `{items,total,limit,offset}`. Sem `oneOf` |
| **NO-020** | 020 / refs / sequence / EPIC-* / RUX-3A fora |
| **SUPPLIER-TAX-ID** | `tax_id` na 026; opcional; unique parcial `(country_code, tax_id)`; dígitos; IT strip `IT`; tax_id exige country |
| **INCOMPLETE-P1** | Filtro `ncm IS NULL OR ean IS NULL`; **não** bloqueia processo |
| **USER-SECURITY** | Foundation HTTP; senha pelo admin; sem e-mail/token; sem editor de `permissions_json`; sem auto-desativar; último admin ativo protegido; audit na mesma UoW |
| **CSV** | **FUTURO** |
| **L-006** | **PARTIAL** — campos na 026; CAP-006 (processo de qualidade) **não** implementado |

## Gates MDM-CF

| Gate | Resultado |
|---|---|
| Pytest V2 completo | **574 passed**, 1 warning, 296.45s — [`logs/mdm-cf-pytest-full.txt`](logs/mdm-cf-pytest-full.txt) |
| OpenAPI drift | `generate:api` + `check:api-drift` OK (antes do walk) |
| Vitest catalog/nav/users | 14 passed no reteste das páginas; suite front 118/119 depois corrigido (cleanup nav) |
| Rebuild `epic_v2_test` | **Só** test DB; DROP SCHEMA public → Alembic 001…026 + admin + DOMESTIC-MAIN — [`mdm_rebuild_test_schema.py`](mdm_rebuild_test_schema.py) |
| Massa | **61** produtos `MDM-SKU-001`…`061` + 4 fornecedores **só** em `epic_v2_test` — [`mdm_cf_seed.py`](mdm_cf_seed.py) |
| Health 8082 | `schema_ok=true`, `alembic_head=026`, `logical_database=epic_v2_test` |
| Walk UI 5174 | tabela abaixo; rascunho de pedido **não** salvo |

`conftest` `drop_all` apaga `epic_v2_test`. Walk **depois** do rebuild. `epic_v2` recebeu só schema nullable 026.

## Walk UI (literal)

Lane: `http://localhost:5174` → `:8082`. Badge **AMBIENTE TESTE**.

| Abri | Vi / Cliquei | Resultado |
|---|---|---|
| `/login` | admin / Entrar | `/orders` |
| Nav | Produtos, Fornecedores, Prestadores, Usuários | DEC-NAV visível |
| `/catalog/products` | lista | **Exibindo 1–50 de 61**; Próxima página |
| offset=50 | | **51–61**; **MDM-SKU-061** |
| `/catalog/products/61` | NCM `61.09.10.00`, EAN, Salvar | API: `ncm=61091000`, `ean=7891234567890` |
| `/catalog/suppliers` | 4 fornecedores massa | Filtro “Sem identificador fiscal” presente |
| `/admin/users` | Administrador + Novo usuário | OK |
| `/logistics-providers` | rail Logística; busca | OK (vazio pós-rebuild) |
| `/orders/new` | SKU `MDM-SKU-061` + Adicionar linha | Linha **MDM-SKU-061** (picker não trata os 50 primeiros como catálogo) |

Screenshots: [`screenshots/mdm-01-nav-orders.png`](screenshots/mdm-01-nav-orders.png) · [`screenshots/mdm-02-products-page2.png`](screenshots/mdm-02-products-page2.png) · [`screenshots/mdm-03-order-picker-061.png`](screenshots/mdm-03-order-picker-061.png).

Pós-walk (polimento, sem reabrir campanha): botão **Buscar** nas listas; ficha espelha NCM/`tax_id` normalizados após PATCH.

## Entregas por fatia

- **MDM-1** — PATCH; list-report; User CRUD Foundation; OpenAPI.
- **MDM-2** — rail Produtos + Administração condicional; pickers `q`; createSku exige descrição.
- **MDM-3** — fichas Product/Supplier (campos atuais + L-006 / `tax_id`).
- **MDM-4** — Alembic **026** em `epic_v2` (nullable) e `epic_v2_test`; NCM 8 dígitos; size/color distinct; peso `> 0`.
- **MDM-5** — UI Usuários; Prestadores no rail Logística; `GET /api/logistics-providers?q=`.
- **MDM-CF** — pytest + rebuild + massa + walk.

## Fora desta campanha (intocado)

Settlement CUSTOMS_FUNDING; J#5-REC; J#6; 020/RUX-3A; CSV; ProductFamily; CAP-006; pedidos 589 / TESTE-CICLO-001.

## Riscos / divergências declaradas

- L-006 **PARTIAL** ≠ CAP-006. Filtro incompleto não trava pedido/estoque.
- Listas operacionais (`GET /api/products`) permanecem array — clientes antigos intactos.
- Pytest destrutivo **somente** `epic_v2_test`.
- CSV de catálogo continua **FUTURO**.

## Pendências (não bloqueiam DONE)

Nenhuma BLOCKER/MAJOR. Backlog de produto já nomeado: CSV; CAP-006; J#5-REC; pagar numerário.

## Próxima etapa

**Pagar o numerário** (`Treasury settlement for CUSTOMS_FUNDING`) — B.1. Não misturar com cadastros.

## Recomendação

**Aceitar DONE / ENCERRADO.** Roadmap **0.5.125**. Blueprint **0.2.25**. Barras **8/10**. Próxima ação = numerário.

## Evidências âncora (não são o pacote advisor)

`docs/v2/etapa-mdm-ux/` — logs, scripts de rebuild/seed, screenshots do walk.

## Arquivos relevantes (áreas)

- `v2/alembic/versions/026_catalog_l006_tax_id.py`; `v2/app/catalog/*`; `v2/app/foundation/user_routes.py`; `v2/app/identity/*`
- `v2/frontend/src/app-shell/AppShell.tsx`; `features/catalog/*`; `features/admin/*`; pickers em Orders / AP / Payments
- Testes: `tests/test_catalog_api.py`, `test_identity_users_api.py`, `test_logistics_api.py`, `test_orders_billing_a2.py` (pin 026)

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md; docs/README.md; docs/v2/etapa-mdm-ux/MDM_UX_ADVISOR_HANDOFF.md; docs/v2/etapa-mdm-ux/MDM_UX_EXECUTION_PLAN.md; docs/v2/etapa-mdm-ux/P0_RUNTIME.md
- Evidence: docs/v2/etapa-mdm-ux/ (logs, scripts, screenshots)
- Roadmap status: 0.5.124 → 0.5.125; MDM-UX DONE; Alembic 026; barras inalteradas 8/10; próxima = pagar numerário
- Next TODO: pagar numerário (Treasury settlement CUSTOMS_FUNDING)
- Return to advisor: docs/v2/etapa-mdm-ux/MDM_UX_ADVISOR_HANDOFF.md
```
