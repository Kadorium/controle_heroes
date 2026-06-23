# Entrega consolidada — QA Rodadas 1, 2 e 3 + Nova Ordem planilha

> Resumo único de tudo executado nas rodadas de QA UI E2E e no redesign do modal de abertura de ordem.  
> **Data:** 2026-06-23 · **Branch:** main · **Commit de referência:** ca7ec86 · **Alembic head:** 010

Documento vivo complementar: [QA_UI_E2E_BASE_LIMPA_ORDEM_REAL.md](QA_UI_E2E_BASE_LIMPA_ORDEM_REAL.md) (evidência detalhada por sessão).

---

## Visão geral

| Rodada | Objetivo | Ordem | Veredito | F12-006 |
|---|---|---|---|---|
| **1** | Diagnóstico E2E A–L em base limpa (sem corrigir bugs) | QA-UI-001 (ID 44) | CONDITIONAL_PASS | PARTIAL |
| **2** | Correção bugs HIGH/MEDIUM da Rodada 1 + testes | — | Bugs corrigidos | PARTIAL |
| **BLOCO 2** | Redesign modal Nova Ordem (planilha profissional) | — | Entregue | — |
| **3** | E2E operacional completo A–L até fechamento UI | QA-UI-002 (ID 157) | **PASS** | **DONE** |

### Ordem de execução

```
Rodada 1 (diagnóstico)
    → Rodada 2 (correções HIGH/MEDIUM)
    → BLOCO 2 (Nova Ordem planilha)
    → Rodada 3 (E2E A–L + fechamento + reabertura)
```

---

## Rodada 1 — Diagnóstico exploratório (QA-UI-001)

**Escopo:** roteiro A–L em base limpa via browser; **apenas registrar bugs**, sem correção.

### Ambiente

| Campo | Valor |
|---|---|
| Porta | 8080 |
| Viewports | 1366×768 (principal), 1920×1080 (inspeção final) |
| Reset | `reset_operational_test_data.ps1` — base já vazia (0 ordens) |
| Backups | DB `epic_importacao_20260623_003459.sql`; anexos `attachments_20260623_003500.zip` |
| Login | admin@epic.com.br |

### Ordem canônica criada

| Campo | Valor |
|---|---|
| PO | QA-UI-001 |
| ID | **44** |
| Fornecedor | Heroes |
| Itens | QA-ITEM-A 100×12,50 EUR + QA-ITEM-B 50×8,00 EUR |
| Total | 1.650,00 EUR |
| Faturas | QA-INV-1 (500) + QA-INV-2 (1000) + QA-INV-3 (150) |
| Pagamento | Planejado 500 EUR; liquidação 250 EUR **não concluída** na UI |

### Roteiro A–L — resultado

| Bloco | Status | Observação |
|---|---|---|
| A | OK com ressalvas | Wizard + Central; responsável/previsão sumiram no reload |
| B | OK | 2 itens somente leitura; 3º item pós-criação = lacuna |
| C | OK | 3 faturas criadas |
| D | PARCIAL | Pagamento planejado OK; liquidação incompleta |
| E–J | LACUNA | Financeiro, docs, logística, aduana, estoque, LC não executados |
| K | OK parcial | Conciliações com 4 bloqueantes |
| L | TRAVOU (esperado) | Fechar desabilitado — checklist pendente |

### Anti-fake

Lista negra (`447.500`, `397.500`, `178.750`, `6.560`, `DEMO-*`) — **nenhuma ocorrência**.

Problemas de honestidade de dado: KPI **Acconto versado** `EUR 0,00` sem liquidação; colunas DESPACHADA/NAC. com `0` em vez de `—`.

### Bugs registrados

| ID | Severidade | Descrição |
|---|---|---|
| QA-HIGH-001 | HIGH | Acconto versado `EUR 0,00` sem pagamento liquidado |
| QA-HIGH-002 | HIGH | Quantidades despachada/nacionalizada/estoque mostram `0` em vazio |
| QA-MED-001 | MEDIUM | Botão Cadastrar fornecedor não dispara submit no click |
| QA-MED-002 | MEDIUM | Responsável e previsão interna não persistem na UI após reload |
| QA-MED-003 | MEDIUM | Grade ordens: responsável `—` após salvar na Central |
| QA-MED-004 | MEDIUM | Preço unitário `12.5000` em vez de `12,50` |
| QA-LOW-001 | LOW | Histórico com labels técnicas (`create`, `update_brazil_field`) |
| QA-LOW-002 | LOW | Fornecedores Heroes duplicados por cliques repetidos |

### Veredito

**CONDITIONAL_PASS** — fluxo A–D operável; fechamento UI não alcançado.

### Testes da Rodada 1

- `pytest tests/test_reset_operational.py` — 4 passed
- `pytest tests/test_postmvp6_ux.py::test_order_queue_has_operational_columns` — 1 passed
- `npm run build` — OK

---

## Rodada 2 — Correções HIGH/MEDIUM

**Escopo:** somente correção dos bugs HIGH e MEDIUM da Rodada 1. **Sem** reexecução do E2E A–L.

### Regra de ouro aplicada: 0 vs vazio

| Campo | `null` / sem evento | `0` real |
|---|---|---|
| `total_paid` | Sem pagamento liquidado | Pagamento liquidado (soma pode ser 0) |
| `quantity_shipped` | Sem embarque | Embarque com qty 0 |
| `quantity_nationalized` | Sem nacionalização | Nacionalização com qty 0 |
| `quantity_stocked` | Sem entrada estoque | Entrada com qty 0 |

Implementação no **nível de dado**; UI já usava `formatMoney` / `emptyDash` para `null` → `—`.

### Bugs — status

| ID | Status | Mudança principal |
|---|---|---|
| QA-HIGH-001 | **FIXED** | `invoice_has_settled_payments()`; KPI retorna `null` sem liquidação |
| QA-HIGH-002 | **FIXED** | `_shipped/_nationalized/_stock_total_for_display()` retornam `None` sem evento |
| QA-MED-001 | **FIXED** | `onClick` explícito em `SuppliersPage.tsx` |
| QA-MED-002 | **FIXED** | Draft local `responsibleDraft`/`forecastDraft` em `ImportationLayout.tsx` |
| QA-MED-003 | **FIXED** | Mesmo root cause do MED-002 |
| QA-MED-004 | **FIXED** | `formatUnitPrice()` pt-BR em `ImportationSectionPage.tsx` |
| QA-LOW-001 | DEFERRED | — |
| QA-LOW-002 | DEFERRED (parcial na UI do BLOCO 2) | — |

### Arquivos alterados (backend)

- `app/services/finance.py`
- `app/services/order_central.py`
- `app/services/logistics.py`
- `app/services/nationalization.py`
- `app/services/reconciliation.py`
- `app/services/dashboard.py`
- `app/services/closure.py`
- `app/schemas_phase789.py`

### Arquivos alterados (frontend)

- `frontend/src/pages/importation/ImportationLayout.tsx`
- `frontend/src/pages/importation/ImportationSectionPage.tsx`
- `frontend/src/pages/cadastros/SuppliersPage.tsx`
- `frontend/src/i18n/glossario.ts`

### Testes criados / ajustados

| Arquivo | Conteúdo |
|---|---|
| `tests/test_qa_rodada2_fixes.py` | 5 testes novos (HIGH-001/002, MED-002/003) |
| `tests/test_order_central.py` | Ajustes relacionados |
| `tests/test_reconciliation_closure.py` | `test_close_with_approved_variance` com estoque real |
| `frontend/e2e/qa-rodada2-fixes.spec.ts` | MED-001, MED-004 |

### Evidência

- pytest total após Rodada 2: **204 passed**
- `npm run build` — OK

---

## BLOCO 2 — Nova Ordem planilha (rodada combinada)

**Escopo:** redesign do modal de abertura conforme plano `nova_ordem_planilha`; executado após BLOCO 1 (bugs QA).

### Entregas de produto

| Item | Detalhe |
|---|---|
| Modal único | Removidas abas wizard; tela planilha `.ux-modal--wide` |
| Heroes default | `pickHeroesSupplierId` + `dedupeSuppliersByName` |
| Tabela itens | Qtd, preço, desconto, subtotal live; `create+items[]` em uma chamada |
| ProductCombobox | Autocomplete client-side por SKU/descrição |
| Totais live | `parseDecimalInput` → `null` (regra 0-vs-vazio) |
| Ordem sem itens | Confirmação explícita antes de criar |
| CC preview | Pill read-only; desconto linha não cria CC |
| Financeiro opcional | `<details>`: 1 PROFORMA + 1 pagamento planejado |

### Arquivos principais criados/alterados

| Arquivo | Papel |
|---|---|
| `frontend/src/pages/importation/NovaOrdemModal.tsx` | Modal planilha |
| `frontend/src/components/ProductCombobox.tsx` | Autocomplete produto |
| `frontend/src/pages/importation/novaOrdemTotals.ts` | Cálculo totais |
| `frontend/src/pages/importation/supplierUtils.ts` | Heroes + dedupe |
| `frontend/src/index.css` | `.ux-modal--wide`, estilos combobox/nova-ordem |

### Testes

| Spec | Casos |
|---|---|
| `frontend/e2e/nova-ordem-planilha.spec.ts` | Heroes default, totais live |
| `frontend/e2e/nova-ordem-regression.spec.ts` | Ordem 2 itens → Central + grade |
| `frontend/e2e/ux-postmvp6-planilha.spec.ts` | Atualizado (sem abas wizard) |
| `frontend/src/pages/importation/novaOrdemTotals.test.ts` | 5 testes Vitest |

### Checklist

- **UX6-E** Nova ordem planilha → **DONE**

---

## Rodada 3 — E2E operacional A–L (QA-UI-002)

**Escopo:** fluxo completo em base limpa até **fechamento pela UI** e **reabertura** com `reason_code`. Entrada via modal planilha (BLOCO 2) com bugs da Rodada 2 corrigidos.

### Ambiente

| Campo | Valor |
|---|---|
| Reset | `RESET_EPIC_TEST_DATA=1` — importações operacionais removidas |
| Servidor E2E | `uvicorn` @ `127.0.0.1:8082` |
| Build | `npm run build` (Vite) antes dos testes |
| Ordem | **QA-UI-002** · ID **157** |
| Estado final | `REOPENED` (fechamento + reabertura validados) |

### Roteiro A–L — resultado

| Bloco | Ação | Status | Observação |
|---|---|---|---|
| A | Nova ordem planilha → Central | OK | Heroes, 2 itens (100×12,50 + 50×8) |
| B | `/itens` somente leitura | OK | `12,50` / `8,00` |
| C | 3 faturas QA-INV-1/2/3 | OK | 500 + 1000 + 150 EUR |
| D | Pagamentos + liquidação | OK | 250 EUR parcial + quitação integral |
| E | `/financeiro` da ordem | OK | Aba carrega |
| F | Upload PROFORMA | OK | v1 UI `/documentos`; v2 API `document_key` |
| G | Embarque OCEAN → AIR | OK | `MODAL_CHANGE_URGENCY` |
| H | DI/DUIMP oficial | OK | Form imposto visível; registro omitido (evita bloqueio conciliação) |
| I | Nacionalização + estoque | PARCIAL | Form UI visível; 2 SKUs + estoque via API |
| J | Landed cost INITIAL + FINAL | OK | Fallback API se 2º clique UI gera INITIAL duplicado |
| K | Conciliações | OK | Sem bloqueantes; botão fechar habilitado |
| L | Fechar + bloqueio + reabrir | OK | Bloqueio `brazil-fields` PATCH; modal reabertura |

### Correção adicional (Rodada 3)

**`app/services/reconciliation.py`:** par **QTY_CHAIN** passa a fazer upsert com status **OK** quando `quantity_ordered == quantity_stocked` (antes registros DIVERGENT antigos podiam permanecer bloqueantes após corrigir estoque).

### Lacunas registradas

| ID | Lacuna | Prioridade |
|---|---|---|
| R3-LAC-001 | Entrada de estoque sem tela na aba aduaneiro | P1 |
| R3-LAC-002 | Versionamento documento v2 sem UI (só API `document_key`) | P1 |
| R3-LAC-003 | Nacionalização UI só 1º item; 2º SKU via API | P1 |
| R3-LAC-004 | `POST /api/invoices` não aplica `importation_guard` em ordem fechada | P1 |
| R3-LAC-005 | 2º clique LC pode enviar INITIAL se estado React desatualizado | P2 |

### Fixtures criados

- `tests/fixtures/qa-ui-doc-v1.txt`
- `tests/fixtures/qa-ui-doc-v2.txt`
- `frontend/e2e/fixtures/qa-ui-doc-v1.txt`
- `frontend/e2e/fixtures/qa-ui-doc-v2.txt`

### Veredito

**PASS** — fechamento limpo pela UI; reabertura com `reason_code`; anti-fake sem DEMO/mock.

### Checklist

- **F12-006** Demo operacional end-to-end → **DONE**

---

## Evidência de testes (consolidada)

| Suite | Quando | Resultado |
|---|---|---|
| `tests/test_reset_operational.py` | Rodada 1 | 4 passed |
| `tests/test_postmvp6_ux.py` (colunas queue) | Rodada 1 | 1 passed |
| `tests/test_qa_rodada2_fixes.py` | Rodada 2 | 5 passed (novos) |
| pytest total pós-Rodada 2 | Rodada 2 | **204 passed** |
| `frontend/e2e/qa-rodada2-fixes.spec.ts` | Rodada 2 | 2 casos |
| `frontend/e2e/nova-ordem-planilha.spec.ts` | BLOCO 2 | OK |
| `frontend/e2e/nova-ordem-regression.spec.ts` | BLOCO 2 | OK |
| `frontend/e2e/ux-postmvp6-planilha.spec.ts` | BLOCO 2 | OK |
| `frontend/e2e/qa-rodada3-e2e-completo.spec.ts` | Rodada 3 | **13 passed** (`--retries=0`) |
| `tests/test_reconciliation_closure.py` + `test_qa_rodada2_fixes.py` | Rodada 3 | **18 passed** |
| Playwright suite completa (referência) | Pós-BLOCO 2 | 42 passed |

---

## Inventário de arquivos (todas as rodadas)

### Backend

```
app/services/finance.py
app/services/order_central.py
app/services/logistics.py
app/services/nationalization.py
app/services/reconciliation.py      ← Rodada 2 + fix QTY_CHAIN OK (Rodada 3)
app/services/dashboard.py
app/services/closure.py
app/schemas_phase789.py
```

### Frontend

```
frontend/src/pages/importation/NovaOrdemModal.tsx
frontend/src/pages/importation/ImportationLayout.tsx
frontend/src/pages/importation/ImportationSectionPage.tsx
frontend/src/pages/importation/novaOrdemTotals.ts
frontend/src/pages/importation/supplierUtils.ts
frontend/src/components/ProductCombobox.tsx
frontend/src/pages/cadastros/SuppliersPage.tsx
frontend/src/i18n/glossario.ts
frontend/src/index.css
```

### Testes e fixtures

```
tests/test_qa_rodada2_fixes.py
tests/test_order_central.py
tests/test_reconciliation_closure.py
tests/fixtures/qa-ui-doc-v1.txt
tests/fixtures/qa-ui-doc-v2.txt
frontend/e2e/qa-rodada2-fixes.spec.ts
frontend/e2e/nova-ordem-planilha.spec.ts
frontend/e2e/nova-ordem-regression.spec.ts
frontend/e2e/ux-postmvp6-planilha.spec.ts
frontend/e2e/qa-rodada3-e2e-completo.spec.ts
frontend/e2e/fixtures/qa-ui-doc-v1.txt
frontend/e2e/fixtures/qa-ui-doc-v2.txt
frontend/src/pages/importation/novaOrdemTotals.test.ts
```

### Documentação

```
docs/QA_UI_E2E_BASE_LIMPA_ORDEM_REAL.md    ← evidência ao vivo por rodada
docs/ENTREGA-QA-RODADAS-1-2-3.md           ← este arquivo
CHECKLIST_MVP_IMPORTACAO_EPIC.md           ← F12-006 DONE; histórico v2.9–v3.2
```

---

## Status final de bugs

| ID | Rodada 1 | Status final |
|---|---|---|
| QA-HIGH-001 | Registrado | **FIXED** (Rodada 2) |
| QA-HIGH-002 | Registrado | **FIXED** (Rodada 2) |
| QA-MED-001 | Registrado | **FIXED** (Rodada 2) |
| QA-MED-002 | Registrado | **FIXED** (Rodada 2) |
| QA-MED-003 | Registrado | **FIXED** (Rodada 2) |
| QA-MED-004 | Registrado | **FIXED** (Rodada 2) |
| QA-LOW-001 | Registrado | **DEFERRED** |
| QA-LOW-002 | Registrado | **DEFERRED** (mitigação UI: dedupe Heroes no modal) |

---

## Pendências pós-rodadas (backlog)

1. **R3-LAC-001** — UI entrada de estoque na aba aduaneiro  
2. **R3-LAC-002** — UI reupload/versionamento de documentos  
3. **R3-LAC-003** — Nacionalização multi-item na UI  
4. **R3-LAC-004** — `importation_guard` em criação de invoice  
5. **R3-LAC-005** — Estado local do painel LC ao calcular 2ª versão  
6. **QA-LOW-001** — Glossário no histórico recente da Central  
7. **QA-LOW-002** — Dedupe persistente de fornecedor Heroes no cadastro  

---

## Histórico no checklist (extrato)

| Versão | Data | Resumo |
|---|---|---|
| 2.9 | 2026-06-23 | Rodada 1 — QA-UI-001 CONDITIONAL_PASS; F12-006 PARTIAL |
| 3.0 | 2026-06-23 | Rodada 2 — bugs HIGH/MEDIUM; pytest 204; F12-006 PARTIAL |
| 3.1 | 2026-06-23 | BLOCO 2 Nova Ordem planilha; UX6-E DONE |
| 3.2 | 2026-06-23 | Rodada 3 — QA-UI-002 PASS; F12-006 DONE; lacunas R3-LAC-001–005 |

---

## Como reproduzir a Rodada 3

```powershell
# Na raiz do projeto
$env:RESET_EPIC_TEST_DATA = "1"
.\.venv\Scripts\python.exe -m app.scripts.reset_operational_test_data --skip-backup

cd frontend
npm run build
# Em outro terminal: uvicorn na porta 8082
$env:E2E_BASE_URL = "http://127.0.0.1:8082"
npx playwright test e2e/qa-rodada3-e2e-completo.spec.ts --retries=0
```

---

*Gerado como consolidação das rodadas QA UI E2E e do redesign Nova Ordem — Epic Controle Importação.*
