# J4-FIN FIN-3B — verificação UI (agente) — **DONE**

| Campo | Valor |
|---|---|
| Etapa | **FIN-3B** |
| Status | **DONE** |
| Data | **2026-08-12** |
| Runtime | `:8081` / `epic_v2` / Alembic **023** / `AMBIENTE: OPERAÇÃO` |
| Asset | **`index-B-ChOX1L.js`** |
| Login | `admin@epic.com.br` |
| Sample | Pedido **FIN3B-244** id **33** (apagado ao final) |
| Invoice | **#24** / número **244** (apagada ao final) |
| Preservado | Pedido **589** id **31** |

Screenshots: `docs/v2/etapa-j4-fin/screenshots/fin3b-*.png`.

---

## Relato literal (clique → o que vi)

### 0. Login e 589 intacto
- Sessão já autenticada em `:8081`.
- Abri `/orders/31`.
- **Vi:** `589` · Heroe's Srl · Confirmado 10/08/2026 14:30:06 · Pedido EUR 830.000,00 · Faturado 0 · Pago 0 · Adiantado 0 · Nenhuma fatura · Nenhuma obrigação · só `Ordine_589 (1) (1).pdf`.
- Shot: `fin3b-order-589-intact.png`.

### 1. Pedido amostra PRODUCT 14.600 @ 50,00 (não 589)
- File picker MCP não seleciona PDF local. Pedido + ingestão via API (cookie sessão), depois walk na UI.
- `POST /api/orders` código `FIN3B-244` · fornecedor Heroe's Srl **id 26** (existente — não criei segundo).
- SKU `8057628953586` (já no catálogo, product id **19**) · qty **14600** PZ @ **50.00** · confirmar.
- URL: `/orders/33`. Confirmado · Pedido **EUR 730.000,00** · Faturado 0 · Nenhuma fatura.
- Shot: `fin3b-order-33-before.png`.

### 2. Ingestão Fattura 244 + Preview Policy A
- Upload API: batch **29** · occ **33** · `run-adapter-fattura` → IR **doc 30**.
- Abri `/ingestion/30`.
- **Vi:** 2 linhas EAN `8057628953586` qty 50 e 150 @ 99,83; Scadenze EUR 5.000,00 + 14.966,00; INFO `MATH_EXPORT_N31`.
- Policy **A** já marcada. Digitei Order ID **33** → **Preview**.
- **Vi:** `Pode commit: sim · ops: 6` · `Policy match: A · Order #33 (CONFIRMED)`.
  - `map_invoice_items`: *Faturar 2 linha(s) do PDF (quantidade e preço do documento, não do pedido)*.
  - SKU … qty PDF **50 @ 99.83** → item **#46** (pedido 50.0000, saldo **14600**).
  - SKU … qty PDF **150 @ 99.83** → item **#46** (pedido 50.0000, saldo **14550**).
  - `warn_price_divergence` (laranja, **não bloqueia**): pedido **50.0000** · Fattura **99.83** nas duas linhas.
- Shots: `fin3b-fattura244-preview-policy.png`, `fin3b-fattura244-preview-match.png`.

### 3. Commit
- **Commit Fattura**.
- **Vi:** `Status: SUCCEEDED · attempt #29` · `create_invoice: SUCCEEDED → Invoice #24` · `Abrir Invoice DRAFT`.
- Shot: `fin3b-fattura244-commit-succeeded.png`.

### 4. Invoice 24 DRAFT
- `/invoices/24`.
- **Vi:** Fatura 244 · Rascunho · pedido FIN3B-244 · Líquido **EUR 19.966,00**.
- Notice **Divergência de preço** (`data-testid="invoice-price-divergence"`): *Fattura ≠ pedido; a fatura segue o documento* · SKU … pedido 50.0000 · Fattura 99.83 (item #46) nas duas linhas.
- Itens: **50 PZ @ EUR 99,83** (4.991,50) e **150 PZ @ EUR 99,83** (14.974,50). Desconto Nenhum.
- PDF `Fattura_244.pdf`. Modo Valor travado. Termos 20/04/2026 5.000 + 30/06/2026 14.966.
- Shot: `fin3b-invoice-24-draft.png`.

### 5. Emitir
- **Emitir** → modal → **Emitir** (sem marcar “sem documento”).
- **Vi:** Status **Emitida** · obrigações Aberto 5.000 e 14.966 · Notice de divergência **permanece**.
- Shot: `fin3b-invoice-24-issued.png`.

### 6. Disponível 14.400 + rastro no pedido
- `/orders/33/commercial` tabela `invoiced-qty`:
  - **Vi:** Item `8057628953586` · Pedida **14.600** · Faturada **200** · Disponível **14.400**. Fatura 244 Emitida EUR 19.966,00.
- `/orders/33` cockpit:
  - **Vi:** Pedido 730.000 · Faturado **19.966,00** · fatura 244 Emitida · obrigações 5.000 + 14.966.
  - Auditoria: **Preço da Fattura diferente do pedido** 12/08/2026 17:50:15 (acima de Confirmação / Item adicionado / Criação).
- Shots: `fin3b-order-33-disponivel-14400.png`, `fin3b-order-33-audit-price.png`.

### 7. 589 depois do ciclo (antes da limpeza)
- `/orders/31` **igual** ao passo 0: Confirmado · 830.000 · zeros · só Ordine.
- Shot: `fin3b-order-589-intact-after.png`.

### 8. Limpeza do sample
- Scripts `logs/fin3b_sample_clean.py` + `fin3b_orphan_clean.py`.
- Apagados: order 33, invoice 24, payables 20/21, IR doc 30, occ 33, batch 29, documento **45** (`Fattura_244.pdf`).
- **Mantidos:** order 31/589 + Ordine; Heroe's Srl id 26; SKU `8057628953586`.
- `/orders/31` depois da limpeza: Confirmado · 830.000 · Faturado 0 · Nenhuma fatura · Nenhuma obrigação.
- Shot: `fin3b-order-589-intact-after-clean.png`.

---

## File picker

| Onde | Resultado |
|---|---|
| Ingestão dropzone | MCP não escolhe arquivo local → upload API (`fin3b_ui_seed.py`) |

---

## 589 — guarda

Confirmado 10/08/2026 14:30:06 · 2 itens COMMITMENT · 0 faturas · 0 obrigações · 0 pagamentos · 0 adiantamentos · documento Ordine único. Não invoiced, não convertido. Sample 33 não tocou neste pedido.
