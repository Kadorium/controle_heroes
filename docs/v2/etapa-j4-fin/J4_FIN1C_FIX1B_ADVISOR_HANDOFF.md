# J4-FIN FIN-1C-FIX-1B — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **FIN-1C-FIX-1B** |
| Status | **DONE** |
| Data | **2026-08-11** |
| Runtime | `:8081` / `epic_v2` / Alembic **022** / `schema_ok` |
| Asset Chromium | **`index-I3tToUDS.js`** (+ `index-B43MO145.css`) |
| Pytest | **471 passed** (ref. 471 — inalterado) |
| Código | só FE (painel + comercial + CSS) |

---

## Decisão

DRYRUN ACEITO. Dois MINORs elevados e consertados **antes** do G6 Ricardo:

| ID | Problema | Decisão |
|---|---|---|
| **C1** | Datas não limpam após registrar (valores limpam) | Reset **completo** — consistência |
| **C2** | Dois file inputs confundíveis (dryrun anexou no pedido) | Separação visual + rótulos + ordem de seções |

Tab/Enter no modal: **fora** — Ricardo valida no G6.

---

## C1 — reset completo

`OrderAdvancesPanel.resetAdvanceForm()` após sucesso limpa: EUR, taxa, BRL, **payment_date**, **execution_date**, referência, arquivo (+ remount do `FileUpload` via `key`).

**Gate UI:** 1º registro EUR 100 @ 6,10 (pay 20/08 ≠ FX 18/08) → todos os campos `""` / “Nenhum arquivo”. 2º registro partiu de formulário vazio (`beforeFill` datas/amount vazios).

---

## C2 — uploads impossíveis de confundir (sem redesenho)

1. Painel **Adiantamentos** movido **acima** de **Documentos**.
2. Bloco visual `Comprovante de câmbio deste adiantamento` dentro do formulário (`name=advance-fx-document`, `accept=pdf`).
3. Botão: `Anexar PDF de câmbio deste adiantamento` + hint anti-Documentos.
4. Documentos: hint + `Anexar documento do pedido (Ordine e afins)` (`name=order-document`).

**Gate UI:** attach só em `[name=advance-fx-document]` → `orderFiles=0`; linha do adiantamento com `fix1b-cambio.pdf`; Documentos do pedido só Ordine.

---

## Gates

| # | Gate | Resultado |
|---|---|---|
| 1 | pytest completo | **471 passed** |
| 2 | Registrar → limpa inclusive datas | PASS |
| 3 | 2º em sequência sem herança | PASS |
| 4 | PDF câmbio → adiantamento, não Documentos | PASS |
| 5 | Ambiente limpo (31 CONFIRMED, 2 linhas, só Ordine) | PASS |
| 6 | Chromium + asset | `index-I3tToUDS.js` · Operação |

---

## Ambiente

Payments de teste **20/21** removidos. SQL: payments `[]` · docs só id **40** Ordine · status CONFIRMED · 2 itens.  
UI: `Nenhum adiantamento registrado`. Screenshot: [`screenshots/fix1b-commercial-empty-after-clean.png`](screenshots/fix1b-commercial-empty-after-clean.png).

---

## Roteiro G6

[`J4_FIN1_G6_ROTEIRO.md`](J4_FIN1_G6_ROTEIRO.md) **segue válido** — atualizado com labels FIX-1B e nota pós-limpeza. Passos 1–9 inalterados na lógica.

## Próxima

**G6 Ricardo** com valores reais do extrato. FIN-1C-FIX-2 (vocab N2 etc.) continua **depois** do G6.

```text
DOC_DELTA
- Updated: OrderAdvancesPanel.tsx; OrderDetailPage.tsx; index.css; J4_FIN1C_FIX1B_ADVISOR_HANDOFF.md; J4_FIN1_G6_ROTEIRO.md; ROADMAP 0.5.101
- Evidence: screenshots/fix1b-*; logs/fin1c-fix1b-pytest.txt; logs/fin1c-fix1b-build.txt
- Roadmap status: 0.5.101 — FIX-1B DONE; next = G6 Ricardo
- Next TODO: G6 Ricardo valores reais 589
- Return to advisor: J4_FIN1C_FIX1B_ADVISOR_HANDOFF.md
```
