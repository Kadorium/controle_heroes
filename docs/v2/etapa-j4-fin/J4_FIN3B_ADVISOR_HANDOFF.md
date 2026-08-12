# J4-FIN FIN-3B — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-3B** (faturamento parcial: qty e preço do PDF) |
| Status | **DONE** |
| Data | **2026-08-12** |
| Runtime | `:8081` / `epic_v2` / Alembic **023** / `AMBIENTE: OPERAÇÃO` |
| Asset | **`index-B-ChOX1L.js`** |
| Pytest | **492 passed** (ref. 486) |
| UI | [`J4_FIN3B_UI.md`](J4_FIN3B_UI.md) — agente percorreu o ciclo; sample limpo |

---

## Estado anterior → atual

| Antes | Depois |
|---|---|
| FIN-3+FIN-2 ACEITOS (0.5.103). P2 MAJOR: `create_invoice` copiava qty integral do pedido | Fattura commit casa linhas do PDF → `replace_items` com qty+preço do documento |
| Pedido 14.600 + Fattura 244 (50+150) estouraria no issue / AMOUNT | Invoice 244: 2 InvoiceItems (50 e 150 @ 99,83) no mesmo OrderItem; líquido EUR 19.966,00 = scadenze |
| Preview Policy A só rodava matching se IR tivesse `supplier_id_catalog` | Preview casa com `order_id` explícito mesmo sem supplier no IR |
| Sem rastro de divergência de preço | Notes + Audit `invoice_price_divergence` na Invoice **e** no Order (mesma UoW); UI Notice |

Order **31 / 589** permanece CONFIRMED, 2 COMMITMENT, zero fatura/obrigação/pagamento/adiantamento. Sample **FIN3B-244** (id 33) + Invoice **24** foram criados, exercitados e **apagados**.

---

## Hipóteses (confirmadas)

1. **Menor correção** — não estender `create_invoice`. Após match: `create_invoice(..., order_item_ids=casados)` + `replace_items` (qty/preço PDF, `discount_type=NONE`).
2. **Uma linha PDF = uma InvoiceItem.** Duas linhas 244 do mesmo EAN (50 e 150) → dois itens, mesmo `order_item_id`. Aduana aloca por `invoice_item_id`.
3. **Disponível = ordered − ISSUED.** DRAFT não reserva; preview avisa `warn_draft_overcommit` se outro DRAFT já cobrir o saldo.
4. **SKU ausente / qty > restante** → preview `can_commit=false` + commit **422** (`fattura_sku_not_on_order` / `fattura_qty_exceeds_remaining`) **antes** de `store_document`. Não vira attempt FAILED.
5. **COMMITMENT-only** → 422 `fattura_no_billable_lines` + mensagem **`nenhuma linha faturável`**. Não é J#5-REC.
6. **Preço** — a fatura segue o PDF; o pedido não muda. Divergência **não bloqueia**. Rastro: notes (`Divergência de preço`) + Audit na invoice e no order.
7. **Match guloso visível** — se >1 OrderItem candidato, preview lista candidatos (escolhido marcado: preço + saldo). Preços diferentes entre candidatos igualmente válidos → `warn_ambiguous_match`. Operador pode mudar o pedido ou seguir.
8. **245 não é “só +80 daquele EAN”.** Segunda fatura de 80 no teste usa API de billing, não o PDF 245.

---

## Entregas

| Área | O quê |
|---|---|
| Match | [`fattura_line_match.py`](../../../v2/app/ingestion/fattura_line_match.py) — PRODUCT por `product_id` ou SKU; guloso por `position`; decrementa restante |
| Commit | Policy A valida o plano **antes** de `store_document`; C2 após reconstruction. `create_invoice` qty-integral **não** alterado |
| Preview | `map_invoice_items`, `match_choice`, `warn_ambiguous_match`, `warn_price_divergence`, `warn_draft_overcommit`, `blocked_*` |
| UI ingestão | [`FatturaCommitPanel.tsx`](../../../v2/frontend/src/features/ingestion/FatturaCommitPanel.tsx) — plano de linhas + candidatos |
| UI fatura | Notice `data-testid="invoice-price-divergence"`; label `invoice_price_divergence` → “Preço da Fattura diferente do pedido”. Label `register` **inalterado** (“Registro”) |
| Rotas | 422 para os três códigos novos; `IngestionError` no commit Fattura também `discard_pending_files` |

---

## Gates

| Gate | Resultado |
|---|---|
| Pytest V2 | **492 passed** — `docs/v2/etapa-j4-fin/logs/fin3b-pytest-full.txt` |
| FIN-3B | 6 testes em `test_j4_fin3b.py` (14600 vs 50+150; 80 via billing; SKU 422; qty 422; COMMITMENT honesto; rastro de preço; match ambíguo) |
| SC-01/02 PERCENT | Intactos (suite completa) |
| FIN-23 / I4 | Intactos; I4 `_create_confirmed_order` agora inclui **todas** as linhas da Fattura 202 a 10× qty PDF (Policy A com qty PDF + AMOUNT) |
| UI ciclo 244 | PASS — ver UI.md |
| 589 preservado | PASS — antes, durante e depois da limpeza |
| Alembic | **023** inalterado; health `schema_ok` |

---

## Decisões / ratificações (não reabrir)

- Faturamento parcial **é** o modelo de negócio (não edge). 244 e 245 na mesma data, DDTs diferentes.
- Invoice segue preço do PDF; pedido não é reescrito.
- DRAFT não reserva saldo.
- Não inventar Product/OrderItem; não partir uma linha PDF em dois OrderItems.
- COMMITMENT permanece recusado com a mensagem honesta já existente.
- FIN-4 **depois** desta fatia. Fora: J#5-REC, J#6, RUX-3A/020, banco.

---

## Riscos / pendências

| Item | Gravidade | Nota |
|---|---|---|
| Fatura manual (`POST /invoices`) ainda copia qty integral | conhecido | Operador edita no DRAFT; só o **commit Fattura** aplica qty PDF |
| Match guloso por `position` | by design | Visível no preview; operador pode reordenar o pedido |
| Coluna AP `Banco / IBAN` `visibility: wide` | MINOR (FIN-23) | Inalterado |
| `BRL REALIZADO` da parcela ignora FX do adiantamento | MAJOR produto / **FIN-4** | Não é desta fatia |
| File picker MCP | operacional | Upload Fattura via API; documentado no UI.md |
| SKU `8057628953586` e Heroe's Srl id 26 | — | Mantidos no catálogo |

Fora de escopo (não iniciado): **FIN-4**, J#5-REC, J#6, RUX-3A/020, integração bancária.

---

## Recomendação

Aceitar FIN-3B. Próxima campanha autorizável: **FIN-4** (custo BRL = soma das execuções; cronograma). Uso 589 continua não-gate. **Não** 3A/020/J#6/J#5-REC.

```text
DOC_DELTA
- Updated: ROADMAP 0.5.104; docs/README timeline; J4_FIN3B_*
- Evidence: etapa-j4-fin/screenshots/fin3b-*; logs/fin3b-*; test_j4_fin3b.py
- Roadmap status: 0.5.104 — FIN-3B DONE; próxima = FIN-4
- Next TODO: FIN-4 quando autorizado; não 3A/020/J#6/J#5-REC
- Return to advisor: docs/v2/etapa-j4-fin/J4_FIN3B_ADVISOR_HANDOFF.md
```
