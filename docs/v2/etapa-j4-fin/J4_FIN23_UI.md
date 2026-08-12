# J4-FIN FIN-3 + FIN-2 — verificação UI (agente) — **DONE**

| Campo | Valor |
|---|---|
| Etapa | **FIN-3 + FIN-2** |
| Status | **DONE** |
| Data | **2026-08-12** |
| Runtime | `:8081` / `epic_v2` / Alembic **023** / `AMBIENTE: OPERAÇÃO` |
| Asset | **`index-JZPf_9mU.js`** |
| Login | `admin@epic.com.br` |
| Sample | Pedido **FIN23-244** id **32** (apagado ao final) |
| Preservado | Pedido **589** id **31** |

Screenshots: `docs/v2/etapa-j4-fin/screenshots/fin23-*.png`.

---

## Relato literal (clique → o que vi)

### 0. Login e 589 intacto
- Abri `/login` → e-mail / senha → **Entrar** → `/orders`.
- Abri `/orders/31`.
- **Vi:** `589` · Heroe's Srl · Confirmado 10/08/2026 14:30:06 · Pedido EUR 830.000,00 · Faturado 0 · Pago 0 · Adiantado 0 · Nenhuma fatura · Nenhuma obrigação · só `Ordine_589 (1) (1).pdf`.
- Shot: `fin23-order-589-intact.png`.

### 1. Pedido amostra PRODUCT (não 589)
- `/orders/new`.
- Código `FIN23-244` · Fornecedor **Heroe's Srl** (id 26, existente — não criei segundo).
- SKU `8057628953586` → **Criar SKU** → linha 50 PZ @ 99,83 → linha 150 PZ @ 99,83 (não agrupei).
- **Vi total:** EUR 19.966,00.
- **Salvar e confirmar** → modal → **Confirmar**.
- URL: `/orders/32`. Confirmado · Pedido EUR 19.966,00 · Nenhuma fatura.
- Shots: `fin23-order-create-244.png`, `fin23-order-32-confirmed.png`.

### 2. Ingestão Fattura 244
- Fila `/ingestion`: dropzone visível. **File picker do browser MCP não seleciona PDF local.**
- Upload via API (cookie sessão): batch 28 · occ 32 · `POST .../run-adapter-fattura` → IR **doc 29** `FATTURA_VENDITA`.
- Abri `/ingestion/29`.
- **Vi:** 2 linhas EAN `8057628953586` qty 50 e 150 @ 99,83; Scadenze EUR 5.000,00 + 14.966,00; campo `destination_iban` `IT82G0707236590000000446136`; banco EMIL BANCA…; issue INFO `MATH_EXPORT_N31` (esperado); **sem** `UNPARSED_LINE`.
- Policy **A** já marcada. Campo **Order ID (obrigatório)** vazio.
- Digitei `32` → **Preview**.
- **Vi:** `Pode commit: sim` · `Policy match: A · Order #32 (CONFIRMED) · Invoice: será criada` · ops store_document / create_invoice / set_terms / link_document.
- **Commit Fattura**.
- **Vi:** `Status: SUCCEEDED · attempt #28` · `create_invoice: SUCCEEDED → Invoice #23`.
- Shots: `fin23-fattura244-review-policy-a.png`, `fin23-fattura244-commit-succeeded.png`.

### 3. Invoice 23 DRAFT → emitir
- `/invoices/23`.
- **Vi:** Fatura 244 · Rascunho · FIN23-244 · Líquido EUR 19.966,00 · desconto **Nenhum** nas duas linhas · PDF `Fattura_244.pdf`.
- Modo **Valor** (select só essa opção, disabled).
- Notice: *Scadenze literais do documento (valores impressos). Percentual recalcularia e ignora esses valores — bloqueado nesta fatura.*
- Termos 20/04/2026 EUR 5.000,00 · 30/06/2026 EUR 14.966,00.
- **Emitir** → modal → **Emitir** (sem marcar “sem documento”).
- **Vi:** Status **Emitida** · obrigações Aberto 5.000 e 14.966.
- Shots: `fin23-invoice-23-draft-amount-lock.png`, `fin23-invoice-23-issued.png`.

### 4. Fila AP + destino de pagamento
- `/payables?pending=OPEN_BALANCE` · Pedido (ID) `32` · **Atualizar**.
- **Vi:** 2 linhas Heroe's · fatura 244 · 5.000 e 14.966 · Aberto · links Câmbio `/payables/18/fx` e `/payables/19/fx`.
- Coluna **Banco / IBAN** não apareceu neste viewport (`visibility: wide` no código).
- `/payables/18/fx`:
  - **Vi:** Banco `EMIL BANCA CREDITO COOPERATIVO ARGILATO` · IBAN `IT82G0707236590000000446136` · Saldo 5.000 · Aberto.
  - Painel **Crédito do pedido**: *Adiantamento do pedido #32. Não é aplicado automaticamente…* · *Nenhum crédito em aberto neste pedido.* · **Pagar saldo restante**.
- Shots: `fin23-ap-queue-order-32-iban.png`, `fin23-payable-18-iban-credit-empty.png`.

### 5. Adiantamento no pedido 32 (não no 589)
- `/orders/32/commercial#order-advances`.
- Valor EUR 600 · taxa 5,9523 · datas 12/08/2026 · **sem PDF** (admin).
- **Vi preview:** BRL derivado 3.571,38.
- **Registrar adiantamento**.
- **Vi:** Total adiantado EUR 600,00 → BRL 3.571,38 · taxa 5,952300 · linha 12/08/2026.
- Shot: `fin23-order-32-advance-600.png`.

### 6. Aplicar crédito (manual)
- Voltei `/payables/18/fx`.
- **Vi:** *Adiantamento EUR 600.00 pago em 12/08/2026 à taxa 5.952300* + **Aplicar neste vencimento** (não aplicou sozinho).
- Cliquei **Aplicar neste vencimento**.
- **Vi:** Saldo EUR 4.400,00 · Status **Parcialmente pago** · crédito em aberto some.
- Shots: `fin23-payable-18-credit-visible.png`, `fin23-payable-18-partially-paid.png`.

### 7. Pagar saldo restante + FX próprio
- Cliquei **Pagar saldo restante**.
- URL: `/payments/new?supplier_id=26&payable_id=18&amount=4400.0000&currency=EUR&order_id=32`.
- Banner: *Contexto da fila: Heroe's Srl · obrigação selecionada · pedido vinculado · valor sugerido EUR 4.400,00.*
- Marquei **Registrar sem documento** · motivo `DOC_OVERRIDE_UI` · **Registrar** → **Confirmar registro**.
- `/payments/24`. Elegíveis: parcela 5.000 (saldo 4.400) e 14.966 (mesmo pedido 32).
- Alocar 4.400 na primeira linha → **Alocar** → confirmar.
- **Vi:** alocação EUR 4.400,00 na obrigação.
- File picker de evidência FX **bloqueado**. Registrei execução via API: EUR 4400 @ **6,10** (sem documento, `FIN23_UI_FILE_PICKER`) → BRL 26.840,00 · link alocação · freeze valuation (exigiu plano INITIAL 6,00 na parcela).
- `/payables/18/fx` depois:
  - **Vi:** Saldo EUR 0,00 · Status **Pago** · IBAN intacto.
  - **BRL REALIZADO BRL 26.840,00** (só o remainder). Não inclui 3.571,38 do adiantamento. Soma verdadeira = 30.411,38.
- Shot: `fin23-payable-18-paid-brl.png`.

### 8. 589 depois do ciclo (antes da limpeza)
- `/orders/31` **igual** ao passo 0: Confirmado · 830.000 · zeros · só Ordine.
- Shot: `fin23-order-589-intact-after.png`.

### 9. Limpeza do sample
- Script `logs/fin23_sample_clean.py` + `fin23_orphan_clean.py`.
- Apagados: order 32, invoice 23, payables 18/19, payments 23/24, FX 20/21, IR doc 29, batch 28, documento órfão Fattura_244, batch vazio 27.
- **Mantidos:** order 31/589 + Ordine; Heroe's Srl id 26; SKU `8057628953586`.

---

## Fatura manual sem PDF (não percorrida nesta sessão)

Código em `InvoiceDetailPage`: `useState("AMOUNT")`; se `terms_from_document` é false, o select oferece Valor **e** Percentual. Travamento só quando a Fattura gravou scadenze literais.

---

## File picker

| Onde | Resultado |
|---|---|
| Ingestão dropzone | MCP não escolhe arquivo local → upload API |
| Evidência FX do remainder | idem → `POST /api/payments/24/fx-executions` sem documento |

---

## 589 — guarda

Confirmado 10/08/2026 14:30:06 · 2 itens COMMITMENT · 0 faturas · 0 obrigações · 0 pagamentos · 0 adiantamentos · documento Ordine único. Não invoiced, não convertido.
