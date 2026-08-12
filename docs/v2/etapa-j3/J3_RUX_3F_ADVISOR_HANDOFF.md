# J3-RUX — RUX-3F ADVISOR HANDOFF

| Campo | Valor |
|---|---|
| Etapa | **RUX-3F** |
| Status | **DONE** (I1 implementado; I0/I2/I3 + Ajustes 1–4 reportados) |
| Data | 2026-08-10 |
| Runtime evidência UI | `:8081` / `epic_v2` · dist `index-CJ3jYOR5.js` |
| Aceite UI I1 | **Pendente Ricardo (G6)** |
| Verificação agent Browser | **PASS** 3/3 — [`J3_RUX_3F_UI_VERIFICATION.md`](J3_RUX_3F_UI_VERIFICATION.md) (não substitui G6) |

**Preservado:** Order **31** code `589` status **CONFIRMED** em `epic_v2` (não apagado).

---

## 6. Ajuste 1 — Status real Order 589

| Campo | Valor |
|---|---|
| id | **31** |
| code | `589` |
| status | **`CONFIRMED`** |
| items | #42 / #43 COMMITMENT (14.600 / 2.000) |
| Audit | `audit_log` id **913** · `action=confirm` · `reason_code=ORDER_CONFIRM_WITH_COMMITMENT` · `2026-08-10 14:30:06` · details `commitment_count=2` |

**Conclusão:** a hipótese “pedido ainda em RASCUNHO” do dry-run **não** se aplica ao aceite do Ricardo. O print sem badge / memória de DRAFT diverge do estado real. A ordem das checagens em `create_invoice` (CONFIRMED **antes** de faturável) **mantém-se**; o erro `"nenhuma linha faturável"` é coerente com CONFIRMED + só COMMITMENT. Gate UI do I1 permanece: esconder create quando `billable=false` em todas as linhas.

---

## 1. I0 — Fattura: I.V. ou EAN? + Ajuste 2 (chave Ordine)

**I0:** **(b) SKUs finais com EAN** (corpus 202/328, adapter `fattura_heroes_v1`, golden I4). Ordine usa `I.V.*`. Q3=B mantém-se.

**Ajuste 2 — a Fattura referencia o número do Ordine?**

**NÃO** nos extracts Heroe's disponíveis.

Trecho Fattura_202 (`docs/v2/_tmp_pdf_extract/Fattura_202.txt`):

```text
Numero: 202
Del: 30/03/2026
...
DDT 389 - 30/03/2026
8057628950936 WASH BAG REBEL - PURPLE ...
```

Trecho Fattura_328:

```text
Numero: 328
Del: 18/05/2026
DDT 594 - 18/05/2026
8057628953593 RACCHETTA BT 2026 STARLIGHT ...
```

- Cita **DDT** (remessa), **não** “Vs. Ordine” / número de pedido.
- Adapter extrai `ddt_ref`, **não** campo de Ordine/PO (`fattura_heroes_v1._extract_header`).

**Implicação RUX-4:** **não há chave técnica comum** linha↔linha (I.V. ↔ EAN) nem âncora documento↔documento Ordine no PDF amostrado. Reconciliação dependerá de **regra de negócio a definir com o Ricardo** (custo/risco do RUX-4 sobe). Hipótese “Fattura cita 589 → external_ref” **não confirmada** nestes corpora.

---

## 2. I1 — Honestidade painel Faturas (implementado)

### Investigação (fechada)

| Pergunta | Resposta |
|---|---|
| Origem “Disponível” | `order_qty_availability` — todos os itens; agora `available_qty=0` se não billable |
| Confirm antes de faturável? | **Sim** — `"Só é possível faturar ordem CONFIRMED"` primeiro |
| Item #id | Corrigido: descrição + “· compromisso” |

### Entrega

- API `OrderQtyRow`: `line_kind`, `description`, `billable`; Disponível faturável = 0 se COMMITMENT.
- UI: Notice PT; sem `Criar fatura` se zero billable; labels humanos.
- Copy **sem** “fantasma/inválido”.

**Notice literal (G6):**

> Este pedido só tem linhas de compromisso (artigos ainda sem SKU final). As faturas destes itens entram pela importação da Fattura do fornecedor — os produtos reais chegam por ali. Não é possível criar fatura manual aqui.

Screenshot: [`screenshots/rux3f/rux3f-i1-faturas-commitment-only.png`](screenshots/rux3f/rux3f-i1-faturas-commitment-only.png)  
Observado no DOM: Disponível `—`; **sem** botão Criar fatura; badge **Confirmado**.

Arquivos: `v2/app/billing/queries.py`, `routes.py`, `InvoiceDetailPage.tsx`, OpenAPI regenerado.  
Testes: `test_orders_rux3b_commitment.py` (API commitment-only + mixed qty/billable); `OrderInvoicesPanel.test.tsx` (Notice/sem create vs mixed com create).

---

## 3. I2 — Relatório exposição financeira (sem implementar)

| # | Achado |
|---|---|
| a | Confirmar = DRAFT→CONFIRMED + audit. **Não** cria Payable/Invoice/Payment. |
| b | Sem conceito de exposição PO no financeiro; “exposição” atual = Payable aberto. |
| c | Payment sem Invoice possível; **sem** FK Order; ACCONTO não existe na V2. |
| d | Visão “compromissos em aberto” → Reporting read-only / lista pedidos; **não** AP. Residual fino depende RUX-4 (sem chave técnica hoje — ver I0/Ajuste 2). |

**Recomendação:** não virar Payable; I1 já fecha mentira de fatura; exposição comercial = decisão advisor pós-chave RUX-4.

**Payable do compromisso?** Advisor **validado** — só `INVOICE` / `CUSTOMS_FUNDING`.

---

## 4. I3 — Qty edit → Order (+ total absurdo)

**PASS** (`tests/test_ingestion_rux3f_i3.py` em `epic_v2_test`):

1. PATCH qty `14600`→`14601` → commit → `OrderItem.quantity == 14601`.
2. PATCH `total_document=999999999.99` → commit → total comercial ≈ Σ linhas (**não** o absurdo).

**D8 não é decorativo** para qty/preço. Header Total PDF **não** alimenta o commit.

### Ajuste 3 — decisão **(a)**

Resumo Ordine: Total exibido = **soma das linhas** (`totalFromLines`); `total_document` removido da edição de cabeçalho. Família desonestidade fechada nesta fatia.

---

## Gates / fora de escopo

- Sem Fattura import, reconciliação, Product I.V.*, Payable, migration, 3A/020/J#6.
- epic_v2 Order 589 **preservada**.
- Pytest: I3 + commitment (qty/billable) — **4 passed**; Vitest `OrderInvoicesPanel` I1 — **3 passed**; OpenAPI regenerado.

## Próxima etapa lógica

1. **Aceite manual Ricardo (G6)** do painel Faturas I1 (screenshot + Notice). Verificação agent Browser já **PASS** — ver [`J3_RUX_3F_UI_VERIFICATION.md`](J3_RUX_3F_UI_VERIFICATION.md).
2. Decisão advisor: priorizar tela exposição Reporting **vs** desenhar regra de negócio RUX-4 (sem chave Ordine nos PDFs atuais).
3. Sem 3A / 020 / J#6.

```text
DOC_DELTA
- Updated: docs/v2/etapa-j3/J3_RUX_3F_ADVISOR_HANDOFF.md; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; ROADMAP_V2_EPIC.md; docs/v2/etapa-j3/J3_RUX_3F_UI_VERIFICATION.md
- Evidence: docs/v2/etapa-j3/screenshots/rux3f/; v2/tests/test_ingestion_rux3f_i3.py; v2/tests/test_orders_rux3b_commitment.py; v2/frontend/src/features/billing/OrderInvoicesPanel.test.tsx
- Roadmap status: 0.5.92 RUX-3F DONE (I1 testes FE/API fechados nesta rodada)
- Next TODO: aceite G6 Ricardo I1; decisão exposição/RUX-4
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3F_ADVISOR_HANDOFF.md
```
