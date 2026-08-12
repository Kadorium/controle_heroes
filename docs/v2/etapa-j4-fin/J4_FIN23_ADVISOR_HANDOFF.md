# J4-FIN FIN-3 + FIN-2 — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-3 + FIN-2** (campanha invertida: Fattura/Payable antes de alocar crédito) |
| Status | **DONE** |
| Data | **2026-08-12** |
| Runtime | `:8081` / `epic_v2` / Alembic **023** / `AMBIENTE: OPERAÇÃO` |
| Asset | **`index-JZPf_9mU.js`** |
| Pytest | **486 passed** (ref. 473) |
| UI | [`J4_FIN23_UI.md`](J4_FIN23_UI.md) — agente percorreu o ciclo; sample limpo |

---

## Estado anterior → atual

| Antes | Depois |
|---|---|
| FIN-1 ACEITO; FIN-2/FIN-3 NOT_STARTED; Alembic 022 | FIN-3 + FIN-2 **DONE**; Alembic **023** (`destination_iban`/`destination_bank` + `invoices.terms_from_document`) |
| Sem Payable comercial sem Fattura | Fattura 244 → Invoice AMOUNT literal → 2 Payables INVOICE; crédito do pedido aplica **só** no mesmo `order_id` |
| Policy A buscava Order por `supplier+external_ref` | `order_id` **obrigatório** (422 `order_id_required`); matching automático removido |

Order **31 / 589** permanece CONFIRMED, 2 COMMITMENT, zero fatura/obrigação/pagamento/adiantamento. Sample **FIN23-244** (id 32) foi criado, exercitado e **apagado**.

---

## Hipóteses (confirmadas)

1. **D1** — `terms_mode` discrimina AMOUNT (scadenze literais) vs PERCENT (manual). HARD STOP (PERCENT vs D1) **não disparou**. SC-01/02 intactos.
2. **D2** — SKU curto 1–6 dígitos (332/`10878`) gera `UNPARSED_LINE`; `_RE_LINE` `\d{7,16}` **não** alargado. Scan por linha de layout (não `finditer` no texto inteiro — ano `2026`+`PZ` era falso positivo).
3. **D3** — IBAN italiano = 27 chars; extrair **só** após `Pagamento:`, parar em `Scadenze:`; nunca o INTESA do timbre (`IT44Z030693713310000000724`).
4. **D4** — Fattura 244 + Doganale 244 ≠ duas Contas a pagar comerciais (teste: 2 INVOICE, 0 CUSTOMS_FUNDING).
5. **FIN-2** — `allocate_payment` com `payment.order_id` exige `Invoice.order_id` igual; elegíveis filtrados; UI **nunca** auto-aplica.

---

## Entregas

### FIN-3 (P1)

| ID | O quê |
|---|---|
| D1 | Fattura commit: `set_terms(AMOUNT)` + `terms_from_document=True`; `replace_items` com `discount_type=NONE`. PUT PERCENT nessa fatura → 400. UI: modo Valor travado + notice. Default manual = **AMOUNT**; PERCENT continua se `terms_from_document` é false. |
| D2 | `UNPARSED_LINE` visível; math não retorna early em linhas vazias (`MATH_LINES_VS_TAX_BASES` no 332). 202/244 sem UNPARSED_LINE; 244 duas linhas mesmo EAN **não** agrupadas. |
| D3 | IBAN 27 chars; persistido na Invoice e copiado ao Payable. UI: Banco+IBAN em `/payables/{id}/fx`. Coluna fila `Banco / IBAN` existe com `visibility: wide` (não cabe no viewport padrão — ver pendência). |
| D4 | Twin 244 no teste `test_fin3_fattura_244_amount_iban_issue_payables`. |
| Policy A | Sem `order_id` → preview `can_commit=false` + 422 no commit. Com `order_id` explícito, matching não depende de `supplier_id` no IR (evita skip quando catálogo Heroe* é ambíguo). |

Goldens scadenze (adapter): 202 15094+15094; 328 1250+4083; 244 5000+14966; 245/332 no `test_j4_fin23.py`.

### FIN-2 (P3)

- Advance do pedido A **não** aloca no pedido B (mesmo fornecedor).
- UI: painel **Crédito do pedido** na obrigação; botão **Aplicar neste vencimento**; **Pagar saldo restante** leva `order_id` no G02.
- Ciclo UI amostra: crédito EUR 600 visível e **não** auto-aplicado → PARTIALLY_PAID saldo 4400 → remainder EUR 4400 à taxa **6,10** (≠ 5,9523 do adiantamento).

### P2 — Faturamento parcial (**relato; não corrigido**)

| Comportamento | Evidência |
|---|---|
| `create_invoice` copia **qty integral** de cada `OrderItem`. `order_item_ids` = subconjunto de **linhas**, não qty parcial. | `billing/commands.py` `create_invoice` |
| `replace_items` **pode** reduzir qty; UI edita quantidade. | Invoice DRAFT |
| Issue: `already_issued + this_qty > ordered` → 400. **Menos** que o pedido é permitido. Ultrapassar é bloqueado. | `_assert_qty_against_order` |
| Disponível = ordered − issued (**só ISSUED**). COMMITMENT → 0 / “—”. | `OrderInvoicesPanel` / `qty-available-*` |
| Payable amount = líquido da Invoice / termos AMOUNT, **não** total do pedido. | Fattura 244: 19966 ≠ 830000 do 589 |
| Fattura commit chama `create_invoice` **sem** `order_item_ids` → todas as linhas billable na qty do pedido. Pedido 589 (14600) + Fattura 244 (200) **estouraria** líquido vs scadenze €19.966. Por isso a amostra foi um pedido PRODUCT 50+150 @ 99,83. | Não corrigir nesta campanha |

---

## Gates

| Gate | Resultado |
|---|---|
| Pytest V2 | **486 passed** — `docs/v2/etapa-j4-fin/logs/fin23-pytest-full.txt` |
| SC-01/02 PERCENT | Intactos (não relaxados) |
| HARD STOP D1×PERCENT | Não disparou |
| UI ciclo 244 | PASS — ver UI.md |
| 589 preservado | PASS — antes, durante e depois da limpeza do sample |
| Alembic 023 em `epic_v2` | Aplicado; health `schema_ok` |

---

## Decisões / ratificações

- Campanha **FIN-3 antes de FIN-2** (advisor): sem Fattura não há Payable comercial.
- Sem auto-resolve silencioso Fattura↔Order; sem Payable a partir de COMMITMENT; sem faturar linhas COMMITMENT; sem derivar payables de %.
- IBAN do timbre INTESA é **proibido** como destino de pagamento.
- Custo BRL verdadeiro = **soma das FxExecutions** (adiantamento + saldo). A visão “BRL realizado” da parcela mostrou só a execução do remainder (`26.840,00` = 4400×6,10), **não** os `3.571,38` do adiantamento. Cockpit média ponderada ≠ custo. **Não é FIN-4** — não “consertar” aqui.

---

## Riscos / pendências

| Item | Gravidade | Nota |
|---|---|---|
| Fattura commit fatura **qty do pedido**, não qty do PDF | MAJOR (conhecido) | Bloqueia 589+Fattura 244 até edição manual de qty. P2 não corrigido. |
| Coluna AP `Banco / IBAN` `visibility: wide` | MINOR | Destino visível na página FX da parcela. |
| `BRL REALIZADO` da parcela ignora FX do adiantamento alocado | MAJOR produto / FIN-4 | Footnote na UI já avisa; número da visão não soma. |
| File picker MCP | operacional | Upload Fattura e evidência FX remainder via API; documentado no UI.md. |
| SKU `8057628953586` e Heroe's Srl | — | Mantidos no catálogo (Heroe's pré-existente). |
| 332/`10878` | by design | Inutilizável até o operador resolver `UNPARSED_LINE`. |
| Fatura manual sem PDF | não percorrida nesta UI | Código: default AMOUNT; PERCENT disponível se `terms_from_document` false. |

Fora de escopo (não iniciado): FIN-4, J#5-REC, J#6, RUX-3A/020, integração bancária, parse FX de PDF.

---

## Recomendação

Aceitar FIN-3 + FIN-2. Próxima campanha autorizável: **FIN-4** (cronograma / custo BRL verdadeiro) **ou** uso real 589 — **não** 3A/020/J#6/J#5-REC. Faturamento parcial (qty PDF vs pedido) precisa de decisão de produto **antes** de ingestão Fattura no 589.

```text
DOC_DELTA
- Updated: ROADMAP 0.5.103; docs/README timeline; J4_FIN23_* 
- Evidence: etapa-j4-fin/screenshots/fin23-*; logs/fin23-*; test_j4_fin23.py
- Roadmap status: 0.5.103 — FIN-3 + FIN-2 DONE
- Next TODO: FIN-4 quando autorizado; não 3A/020/J#6/J#5-REC
- Return to advisor: docs/v2/etapa-j4-fin/J4_FIN23_ADVISOR_HANDOFF.md
```
