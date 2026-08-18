# J4-FIN-CICLO-FIX — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-CICLO-FIX** (C1–C3) |
| Status | **DONE** |
| Data | **2026-08-13** |
| Runtime | `:8081` / `epic_v2` / Alembic **024** / `AMBIENTE: OPERAÇÃO` |
| Asset | **`index-BtTa8d5v.js`** |
| Pytest | **504 passed** (ref. 496) |
| Chromium | Chrome/144.0.7559.236 · Electron/40.10.3 · Cursor/3.14.7 |
| Preservado | Pedido **589** id **31** — CONFIRMED, 2 COMMITMENT, zeros |
| Sample | **TESTE-CICLO-001** id **34** intacto; **TESTE-FIX-C3-b6caebd7** id **35** ficou como prova C3 |

---

## Regra de negócio (C1) — uma frase

**Adiantamento é o dinheiro que saiu pelo painel de adiantamento do pedido; continua adiantamento depois de aplicado às parcelas. Pagamento de saldo é a quitação de uma obrigação, mesmo que carregue o mesmo `order_id`.**

Não é “antes de existir payable” (o segundo adiantamento do CICLO nasceu depois da T-001). Não é “ainda tem residual” (depois de aplicar, o 180.000 continua adiantamento). Distinção no nascimento: `Payment.purpose = ADVANCE` só em `POST /orders/{id}/advances`; `SETTLEMENT` em `POST /payments` com `order_id`.

---

## Entregas

### C1 — “Total adiantado” deixou de ser o caixa inteiro
- Coluna `payments.purpose` (Alembic **024**). Backfill: audit `order_advance=` / `ORDER_ADVANCE` → ADVANCE; resto com `order_id` → SETTLEMENT.
- `GET /orders/{id}/advances`: consolidado **só** ADVANCE; `settlements` à parte.
- Comercial: bloco **Adiantamentos (crédito)** vs **Pagamentos de saldo deste pedido**.
- Cancelar pelo endpoint de adiantamento recusa SETTLEMENT.
- KPI cockpit “Adiantado (crédito)” soma residual só de ADVANCE.

**TESTE-CICLO-001:** Total adiantado **EUR 180.000 / BRL 1.065.000** (120k@5,80 + 60k@6,15). Cinco pagamentos de saldo rotulados à parte (300k + 90k + 30k + 14.966 + 5.000). Não é mais 619.966.

### C2 — “Exposição FX”
O **número** estava certo: saldo aberto das obrigações, na moeda do pedido. O **rótulo BRL** mentia. Corrigido para a moeda do pedido + hint “Saldo aberto nas obrigações, na moeda do pedido”.

- CICLO-001 (tudo pago): **EUR 0,00** (não BRL).
- TESTE-FIX-C3 (parcela aberta): **EUR 1.000,00**.

### C3 — Custo BRL sem F5
`PayableFxPage` incrementa `reloadToken` do `PayableFxPanel` após aplicar crédito. Na mesma passada: flash “Nenhum crédito” no primeiro paint → “Carregando créditos…” até a API.

Prova em payable **29** (pedido 35), **sem F5**: Custo BRL **0,00** → **5.800,00** (1.000 @ 5,80). API confirma `cost_brl=5800.00`.

---

## Gates

| Gate | Resultado |
|---|---|
| 1. Pytest completo | **504 passed** (ref. 496) |
| 2. CICLO-001 adiantamento vs saldo | PASS — 180k vs 5 saldos rotulados |
| 3. Exposição FX moeda coerente | PASS — EUR, não BRL |
| 4. Aplicar crédito → custo BRL sem F5 | PASS — before/after payable 29 |
| 5. 589 intacto; CICLO-001 preservado | PASS |
| 6. Chromium + asset | Chrome/144.0.7559.236 · `index-BtTa8d5v.js` |

Vitest: `PayableFxPage.test.tsx` cobre o refetch. Falha pré-existente `IngestionPages.test.tsx` (`ingestion-tech-details`) **não** é desta fatia.

---

## Fora (registrado, não consertado)

Do CICLO §5, inalterados: (1) fatura avulsa copia qty do pedido; (2) FX de saldo exige PDF na UI; (7) faturado > pedido em valor; (8) T-003 manual sem rastro de preço. FIN-4, J#5-REC, J#6, RUX-3A/020.

---

## Decisões

- Marca no nascimento (`purpose`), não residual nem “antes do payable”.
- C2: corrige o **rótulo**; o número já era exposição em moeda estrangeira/do pedido.
- Não auto-ligar FX em `register_execution` (ratificado no CICLO).
- TESTE-CICLO-001 **não** se apaga. TESTE-FIX-C3 id **35** é amostra pequena de prova C3; pode ficar.

## Recomendação

Aceitar FIN-CICLO-FIX. Próxima da campanha SKU (Roadmap 0.5.109): **G3** UI do bind. Próxima fatia financeira, quando autorizada: **FIN-4** cronograma. Não iniciar 3A/020/J#6/J#5-REC.

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; treasury purpose+listagem; reporting advanced_credit; cockpit KPI; PayableFx refetch; credit loading flash; alembic 024; OpenAPI
- Evidence: docs/v2/etapa-j4-fin/screenshots/ciclo-fix-* ; logs/ciclo_fix_c3_seed.py
- Roadmap status: 0.5.110 FIN-CICLO-FIX DONE; Alembic 024; próxima G3 (SKU) / FIN-4 na fila financeira
- Next TODO: G3 (UI bind) quando autorizado; FIN-4 cronograma permanece na fila
- Return to advisor: docs/v2/etapa-j4-fin/J4_FIN_CICLO_FIX_ADVISOR_HANDOFF.md
```
