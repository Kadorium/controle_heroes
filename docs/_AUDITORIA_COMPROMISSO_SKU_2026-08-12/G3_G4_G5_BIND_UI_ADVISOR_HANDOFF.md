# G3+G4+G5 — Bind UI, match Fattura, aceite 589

| Campo | Valor |
|---|---|
| Etapa | **G3 + G4 + G5** (campanha bind compromisso→produto) |
| Status | **DONE** |
| Data | **2026-08-13** |
| Runtime | `:8081` / `epic_v2` / Alembic **024** / Operação |
| Asset | **`index-Cl2q9bsW.js`** |
| Health | `ok`, `schema_ok=true`, `alembic_head=024`, DB `epic_v2` |
| Pytest | **507 passed** (baseline 504; +3 G4) |
| 589 | id **31** — I.V. 2 → PRODUCT `CAT-G5-GRAFICATE`; I.V. 1 permanece COMMITMENT |

---

## Estado encontrado (antes)

- G2: `POST .../bind-product` com códigos reais `line_already_invoiced` / `invalid_product` / `invalid_transition` (422/422/409).
- Comercial: tabela Itens sem ação de bind; SKU preferia `external_code` mesmo após bind.
- Disponível “—” só em Faturas; aviso só-compromisso sumia no estado misto.
- Match Fattura: só `product_id` / `sku_snapshot` — PDF `I.V. 2` falhava após bind.

---

## O que foi feito

### G3 — UI
- [`BindProductModal.tsx`](../../../v2/frontend/src/features/orders/BindProductModal.tsx): busca catálogo, criar inline, recusa SKU `I.V.*`, erros mapeados pelos códigos G2 reais.
- [`OrderDetailPage.tsx`](../../../v2/frontend/src/features/orders/OrderDetailPage.tsx): ação “Vincular produto” só em COMMITMENT+CONFIRMED; coluna Disponível; SKU = `external_code` se COMMITMENT, `sku_snapshot` se PRODUCT.
- [`ordersApi.bindCommitmentProduct`](../../../v2/frontend/src/features/orders/ordersApi.ts) preserva `status`+`code`.
- Vitest: misto explícito + rejeição I.V.* + mapa de erros.

### G4 — Match + aviso
- [`fattura_line_match.py`](../../../v2/app/ingestion/fattura_line_match.py): 3ª chave `external_code == sku` **somente** em `product_items` (`product_id is not None`).
- Aviso Faturas: texto novo; aparece se **qualquer** linha não faturável (estado misto incluso).
- Pytest G4: match por I.V. pós-bind; regressão sku_snapshot; compromisso puro → `fattura_no_billable_lines`.

### G5 — Percurso (Abri / Vi / Cliquei)

**Antes:** health `ok` / alembic `024` / asset `index-Cl2q9bsW.js`.

1. **Abri** `/orders` → **Cliquei** Confirmado → **Cliquei** 589 → **Cliquei** Abrir comercial.
2. **Vi** duas linhas Compromisso (`I.V. 2`, `I.V. 1`), Disponível `—`, dois botões “Vincular produto”.
3. **Cliquei** Vincular produto na I.V. 2. **Vi** modal título “Vincular produto”; linha atual `I.V. 2 · racchette 2027 GRAFICATE · qtd 14.600`; placeholder “Buscar SKU no catálogo…”; Confirmar/Cancelar.
4. **Digitei** `CAT-G5-GRAFICATE`, descrição teste G5 → **Cliquei** Criar produto no catálogo → **Vi** “Selecionado: CAT-G5-GRAFICATE…”.
5. **Cliquei** Confirmar. Sem F5: linha 42 → Produto / `CAT-G5-GRAFICATE` / Disponível `14.600`; botão sumiu.
6. **Vi** linha 43 ainda Compromisso + Vincular (não cliquei).
7. **Vi** aviso Faturas (texto G4 literal) no estado misto.
8. **Recarreguei** a página: estado persistiu.
9. **GET** `/api/orders/31`: item 42 `external_code='I.V. 2'` preservado; `sku_snapshot=CAT-G5-GRAFICATE`.

Passos só por API: nenhum no percurso de bind (criação de produto e bind pela UI). GET de verificação foi API (pedido do G5 §11).

Autocorreção UX: **nenhuma** divergência exigiu patch durante o walk.

---

## Premissas — confirmadas / refutadas

| Premissa | Resultado |
|---|---|
| Códigos G2 = `line_already_invoiced` / `invalid_product` / `invalid_transition` | **Confirmada** (lido em commands + `_map_error`) |
| `product_items` já filtra `product_id is not None` | **Confirmada** (~L170) |
| Após bind, coluna SKU mostra catálogo (não I.V.*) | **Confirmada** no walk |
| `external_code` permanece no banco | **Confirmada** via GET |
| Aviso aparece no misto | **Confirmada** |
| Suite ≥ 504 | **Confirmada** — 507 |

---

## Atrito UX (anotado, não consertado)

- Fila Pedidos → Cockpit → Abrir comercial: **dois cliques** para chegar aos itens (cockpit intermediário).
- Cancelar pedido permanece no topo do comercial com campo Motivo sempre visível — compete visualmente com Vincular produto.
- Seção Faturas diz “Nenhuma fatura” **e** o aviso de compromisso; o operador pode achar que o aviso fala de faturas inexistentes.
- Após criar produto inline, Confirmar exige segundo clique (criar ≠ vincular) — correto, mas não óbvio no primeiro uso.
- Datalist de SKU não lista descrições no campo (só no “Selecionado:” após match exato).

---

## Fora

Desvincular; converter I.V. 1; importar Fattura real no 589; FIN-4; 3A/020/J#6/J#5-REC.

## Recomendação

Aceitar G3+G4+G5. Próxima canônica: **FIN-4** (cronograma no pedido).

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md · OrderDetailPage · BindProductModal · ordersApi · InvoiceDetailPage (aviso) · fattura_line_match · testes Vitest/pytest · frontend dist
- Evidence: docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/G3_G4_G5_BIND_UI_ADVISOR_HANDOFF.md
- Roadmap status: 0.5.112 G3+G4+G5 DONE; próxima = FIN-4
- Next TODO: FIN-4 cronograma no pedido (quando autorizado)
- Return to advisor: docs/_AUDITORIA_COMPROMISSO_SKU_2026-08-12/G3_G4_G5_BIND_UI_ADVISOR_HANDOFF.md
```
