# G2 — `bind_commitment_product` (backend)

| Campo | Valor |
|---|---|
| Etapa | **G2** — comando + rota + testes (sem UI) |
| Status | **DONE** |
| Data | **2026-08-13** |
| Campanha | Âncora de billing do compromisso (G1 Path A aprovado) |
| Escopo | Backend puro. Sem UI (G3), sem match da Fattura (G4), sem FIN-4, sem converter o 589 |

---

## 0. Estado anterior → atual

**Antes:** pedido CONFIRMED com linha COMMITMENT era somente leitura. `add_item` / `update_item` exigiam DRAFT. Não havia conversão. Faturar respondia *nenhuma linha faturável*.

**Agora:** `POST /api/orders/{order_id}/items/{item_id}/bind-product` vincula um Product **ativo** à linha, na mesma UoW da auditoria `bind_product`. A linha passa a `PRODUCT` com `product_id`; `billable` vira True; disponível = pedida − emitida. O código I.V.* em `external_code` **permanece**. Quantidade, preço e unidade **não mudam**.

O pedido **31 / 589** não foi tocado. Continua CONFIRMED, duas linhas COMMITMENT, `I.V. 2` e `I.V. 1`.

---

## 1. Premissas do contrato vs código — o que mudou

O enunciado pedia UUID e corpo só com `product_id`. O código real usa **int** e lock otimista em toda escrita de pedido. Decisões (executadas):

| Enunciado | Código | Por quê |
|---|---|---|
| `product_id` UUID | `product_id: int` | IDs do catálogo/pedido são inteiros |
| Body `{ product_id }` | `{ expected_version, product_id }` | Toda mutação de Order usa versão; sem isso há lost update |
| Resposta = OrderItem | `OrderResponse` (pedido inteiro, item dentro) | Cliente precisa da `version` para o próximo write; irmãos (`add_item`, `patch_item`) já devolvem o pedido |
| Orders consulta fatura emitida | Comando recebe `issued_qty: Decimal`; a rota lê Billing via `app.foundation.billing_facts` | ADR-11: Orders ↛ Billing (ciclo). Composition root |
| 409 se não CONFIRMED | `invalid_transition` → 409 | Mensagem explícita; **não** reusa `order_not_draft` (“só edita em DRAFT”) |
| 422 produto inexistente | `invalid_product` → 422 (não 404) | `*_not_found` no mapa HTTP viraria 404 |

Auditoria no **comando** (não só na rota), mesma UoW, para quem chamar `orders.public.bind_commitment_product`.

---

## 2. Contrato efetivo

`bind_commitment_product(order_id, item_id, product_id, *, actor, expected_version, issued_qty)`

Pré-condições (todas explícitas):

1. Pedido `CONFIRMED` (DRAFT / CANCELLED / CLOSED → 409).
2. Item `line_kind == COMMITMENT` (já PRODUCT → 422 `item_not_commitment`).
3. `issued_qty == 0` (qty ISSUED nessa linha; DRAFT de fatura **não** bloqueia).
4. Product existe e `is_active`.

Ação (um flush + bump de versão):

- `line_kind = PRODUCT`, seta `product_id`
- `sku_snapshot` / `description_snapshot` ← SKU e descrição do produto
- **não** altera `external_code`, quantidade, preço, unidade
- `record_event(action="bind_product", details={ item_id, from_kind, from_external_code, from_product_id: null, to_product_id, to_sku, actor })`

Pós: `GET /api/orders/{id}/invoiced-quantities` → `billable=true`, `available_qty = ordered − issued`.

Rota: `POST /api/orders/{order_id}/items/{item_id}/bind-product`  
Permissão: `orders:write`.  
Fachada: `orders.public.bind_commitment_product` (outros módulos **não** importam internals).

---

## 3. Gates

| Gate | Resultado |
|---|---|
| Sem migração G2 | **PASS** — G2 não criou revision |
| Alembic aplicado em `epic_v2` | **024** (`Payment.purpose`, C1 concorrente — **não** é G2) |
| Health runtime `:8081` | `ok`, `alembic_head=024`, `schema_ok=true`, lane Operação, DB `epic_v2` |
| Arch (Orders ↛ Billing) | **PASS** — `test_import_boundaries` |
| OpenAPI | Client regenerado; `check:api-drift` limpo; path `bind-product` em `openapi.json` |
| Pedido 31 / 589 | **intacto** — ver §5 |
| UI / `fattura_line_match.py` / FIN-4 | **não alterados** |
| Pytest G2 isolado | **6 passed** (`test_orders_g2_bind_product.py`) |
| Pytest suíte | **504 passed** |

Premissa “head ainda 023” **refutada no runtime**: C1 aplicou `024_payment_purpose` em `epic_v2` enquanto o G2 rodava. G2 **não** criou nem aplicou 024.

---

## 4. Testes

Cobertura pedida:

- CONFIRMED + COMMITMENT sem fatura → 200 + auditoria + `external_code` + snapshots + `billable=True`
- ISSUED na linha → 422 `line_already_invoiced`
- DRAFT → 409 `invalid_transition`
- item já PRODUCT → 422 `item_not_commitment`
- produto inativo / inexistente → 422 `invalid_product`

Suíte limpa após a corrida de lock na `epic_v2_test`: **504 passed** (1 warning Starlette/httpx). Inclui os 6 testes G2. Baseline citada em 0.5.106 era 492.

---

## 5. Pedido 31 (589) — só leitura

```
id=31 code=589 status=CONFIRMED
item 42 COMMITMENT product_id=NULL external_code='I.V. 2' qty=14600 PZ
item 43 COMMITMENT product_id=NULL external_code='I.V. 1' qty=2000 PZ
```

`external_code` **não** foi alterado. Nenhum bind foi executado neste pedido.

---

## 6. Riscos / pendências

- **G3** — picker + modal de confirmação + aviso da Fattura na UI. Sem isso o operador do 589 continua bloqueado na tela.
- **G4** — match da Fattura por `external_code` (I.V.*). Sem isso, depois do bind, o PDF genérico pode não casar com o SKU de catálogo.
- Não criar produto-categoria de verdade nesta fatia (só o comando). G3 pode reusar `POST /api/products`.
- `issued_qty` no comando é contrato público: quem chamar a fachada (não a rota) **precisa** passar a qty ISSUED — senão a guarda de fatura emitida não roda.

---

## 7. Recomendação

Aprovar **G3** (UI, sem converter o 589 até o operador confirmar na cara). FIN-4 permanece na fila, **não** é a próxima desta campanha. Não iniciar 3A/020/J#6/J#5-REC.

---

## 8. Arquivos

Código: `v2/app/orders/commands.py`, `errors.py`, `public.py`, `routes.py`; `v2/app/billing/queries.py`, `public.py`; `v2/app/foundation/billing_facts.py`; `v2/tests/test_orders_g2_bind_product.py`; client OpenAPI gerado.

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md · orders bind · billing issued_qty helper · foundation billing_facts · OpenAPI gerado · este handoff
- Evidence: docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/G2_BIND_PRODUCT_ADVISOR_HANDOFF.md
- Roadmap status: 0.5.109 G2 DONE; próxima ação canônica = G3 (UI, aguarda aprovação)
- Next TODO: G3 UI bind (picker + modal); não converter 589
- Return to advisor: docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/G2_BIND_PRODUCT_ADVISOR_HANDOFF.md
```
