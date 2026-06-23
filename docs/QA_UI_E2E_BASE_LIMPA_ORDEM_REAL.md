# QA UI E2E — Base limpa — Ordem QA-UI-001

> Registro ao vivo da sessão de teste manual exploratório (browser interno Cursor).  
> **Regra:** não corrigir bugs nesta sessão — apenas diagnosticar.

---

## Cabeçalho

| Campo | Valor |
|---|---|
| Início | 2026-06-23 ~00:35 BRT |
| Fim | 2026-06-23 ~00:42 BRT |
| Branch | main |
| Commit | ca7ec86 |
| Alembic head | 010 (head) |
| Testador | Cursor Agent (sessão automatizada) |

---

## Ambiente

| Campo | Valor |
|---|---|
| APP_ENV | development |
| DATABASE_URL | postgresql://postgres@localhost:5433/epic_importacao |
| Porta | 8080 |
| Viewport principal | 1366×768 |
| Viewport inspeção final | 1920×1080 |
| Login | admin@epic.com.br |

---

## Comandos executados

| Comando | Exit code | Observação |
|---|---|---|
| `.\scripts\backup-db.ps1` | 0 | `backups\db\epic_importacao_20260623_003459.sql` |
| `.\scripts\backup-attachments.ps1` | 0 | `backups\attachments\attachments_20260623_003500.zip` |
| `reset_operational_test_data.ps1` | 0 | importations_removed: 0, remaining: false |
| `pytest tests/test_reset_operational.py -q` | 0 | 4 passed |
| `pytest tests/test_postmvp6_ux.py::test_order_queue_has_operational_columns -q` | 0 | 1 passed |
| `npm run build` (frontend) | 0 | vite 1.11s |
| `uvicorn app.main:app --host 127.0.0.1 --port 8080` | 0 | PID 352348, health OK |

---

## Estado inicial (antes do reset)

| Métrica | Valor |
|---|---|
| Ordens | 0 (base já limpa) |
| Fornecedores | 0 (Heroes ausente — criado em Cadastros durante teste) |

---

## Limpeza (reset)

| Campo | Valor |
|---|---|
| Método | reset_operational_test_data.ps1 (sem demo seed) |
| Backup DB | `backups\db\epic_importacao_20260623_003459.sql` (+ interno `20260623_003515`) |
| Backup anexos | `backups\attachments\attachments_20260623_003500.zip` |
| importations_removed | 0 |
| users_preserved | true |
| heroes_supplier_preserved | true |
| importations_remaining | false |
| Base limpa confirmada | sim — grade vazia pós-reset, sem DEMO-* |

---

## Servidor

| Campo | Valor |
|---|---|
| pytest | test_reset_operational.py: 4 passed; test_order_queue_has_operational_columns: 1 passed |
| npm build | OK |
| PID uvicorn | 352348 |
| Health | status ok, database ok |

---

## Tabela de verdade (valores canônicos)

| Campo | Valor |
|---|---|
| PO | QA-UI-001 |
| Fornecedor | Heroes |
| Moeda | EUR |
| Incoterm | FOB |
| Prioridade | Alta |
| Responsável | QA Tester |
| Previsão interna | 2026-12-31 |
| Observação | QA persistência observação 2026-06-23 |
| Item 1 | QA-ITEM-A · 100 × 12,50 EUR |
| Item 2 | QA-ITEM-B · 50 × 8,00 EUR |
| Total pedido | 1.650,00 EUR |
| QA-INV-1 (ANTECIPO) | 500,00 EUR |
| QA-INV-2 (SALDO) | 1.000,00 EUR |
| QA-INV-3 (COMPLEMENTAR) | 150,00 EUR |
| Pagamento planejado | 500,00 EUR · venc. 15/07/2026 |
| Pagamento liquidado | 250,00 EUR · comprovante QA-REC-001 (não concluído na UI) |
| **ID ordem criada** | **44** |

---

## Anti-fake (checagens)

| Momento | Tela | Lista negra? | Zero em vazio? | Status |
|---|---|---|---|---|
| Pós-reset | `/` | Não | Contagens `0` em KPIs globais (aceitável como contagem) | OK |
| Pós-reset | `/importacoes` | Não | N/A (vazia) | OK |
| Pós-wizard | Central | Não | **Sim** — colunas DESPACHADA/NAC. com `0` | **BUG HIGH** |
| Pós-faturas | Central + grade | Não | Acconto versado `EUR 0,00` | **BUG HIGH** |
| Pós-pagamentos | Central KPIs | Não | Valor faturado `1.650` coerente com tabela | OK |
| Final 1920 | `/importacoes` | Não | Só QA-UI-001 na grade | OK |

**Lista negra verificada:** `447.500`, `397.500`, `178.750`, `6.560`, `R$ 1,84`, `R$ 162,6 mil`, `DEMO-*` — **nenhuma ocorrência**.

---

## Roteiro A–L

| Bloco | Tela | Ação | Esperado | Observado | Status |
|---|---|---|---|---|---|
| A | Wizard + Central | Criar QA-UI-001, editar BR, salvar | Central aberta, KPIs coerentes | Ordem ID 44; faixa 3 faturas; prioridade Alta salva; responsável/previsão sumiram no reload do cabeçalho | OK com ressalvas |
| B | `/itens` | Conferir itens | 2 itens somente leitura | 100×12.5 e 50×8 exibidos; sem formulário adicionar | OK |
| B | Lacuna | 3º item | Impossível pós-criação | Confirmado — só via wizard | LACUNA |
| C | `/invoices` | 3 faturas QA-INV-1/2/3 | 500/1000/150 EUR | Criadas; toast possível EN; faixa `.inv-stage` com 3 etapas | OK |
| C | Grade | Col. Faturas | 0/3 | Não verificado numericamente na grade (1 linha) | OK parcial |
| D | Central Pagamentos | Planejado 500 EUR | Não reduz saldo | Pagamento planejado criado; saldo a pagar ainda 1.650 | OK |
| D | Liquidar 250 | Reduz saldo | Botão Liquidar visível; fluxo completo não finalizado | PARCIAL |
| E | `/financeiro` | Crédito/CC | UI cadastro | Aba carrega via sidebar; conteúdo mínimo explorado | LACUNA |
| F | Central Docs | Upload | v1/v2 | Sem documento; upload não testado (sem arquivo fixture) | LACUNA |
| G | `/logistica` | Embarque OCEAN | Criar + trocar modal | "Nenhum embarque"; formulário disponível — não executado | LACUNA |
| H | `/aduaneiro` | DI/DUIMP | Bloqueio sem doc | Não navegado em profundidade | LACUNA |
| I | Estoque | Nacionalizar | Bloqueio estoque > nacionalizado | Não testado | LACUNA |
| J | LC | Calcular versões | UI createLc | Não testado | LACUNA |
| K | `/conciliacao` | Executar conciliações | Divergências | Executado; 4 bloqueantes listados | OK parcial |
| L | Fechamento | Fechar ordem | Bloqueios objetivos | Fechar desabilitado; checklist: PROFORMA, DI, LC FINAL, nacionalização, 4 conciliações | TRAVOU (esperado) |

**Cronômetro bloco A:** ~3 min (wizard + Central) — meta <2 min não atingida (cadastro Heroes + wizard 5 passos).

---

## Viewport 1920×1080

| Área | Densidade/scroll | Colunas | Usabilidade Excel | Notas |
|---|---|---|---|---|
| Grade `/importacoes` | 1 linha visível; scroll horizontal mínimo | Prioridade, responsável, obs. editáveis inline | Adequado para 1 ordem; colunas responsável/previsão vazias na grade | OK |
| Central QA-UI-001 | Seções empilhadas; scroll vertical necessário | Faixa faturas 3 etapas visível com scroll | Denso mas navegável; hub lateral útil | OK |

---

## Bugs

| ID | Severidade | Reprodução |
|---|---|---|
| QA-HIGH-001 | HIGH | Central KPI **Acconto versado** exibe `EUR 0,00` sem pagamento liquidado — deveria ser `—` |
| QA-HIGH-002 | HIGH | Grade itens na Central: colunas DESPACHADA / NAC./RECEB. mostram `0` em vez de `—` para campo vazio |
| QA-MED-001 | MEDIUM | Cadastros → Fornecedores: botão **Cadastrar** não dispara submit via click (funciona com Enter / `form.requestSubmit`) |
| QA-MED-002 | MEDIUM | Cabeçalho Central: **Responsável** e **Previsão interna** salvos mas campos vazios após reload da página |
| QA-MED-003 | MEDIUM | Grade `/importacoes`: coluna responsável mostra `—` após salvar "QA Tester" na Central |
| QA-MED-004 | MEDIUM | Preço unitário na aba Itens: `12.5000` / `8.0000` (formato) vs `12,50` digitado |
| QA-LOW-001 | LOW | Histórico recente exibe ações técnicas `create`, `update_brazil_field` |
| QA-LOW-002 | LOW | Múltiplos fornecedores "Heroes" duplicados após cliques repetidos em Cadastrar |

---

## Parada

| Campo | Valor |
|---|---|
| Ponto máximo | Bloco **L** — fechamento bloqueado (checklist com 4+ pendências) |
| Bloco / passo exato | L — botão "Fechar importação" desabilitado; conciliações com 4 bloqueantes |

---

## Veredito

**CONDITIONAL_PASS**

- Fluxo principal **A–D** operável pela UI (criação wizard, itens, 3 faturas, pagamento planejado).
- **E–L** com lacunas documentadas ou bloqueios esperados de negócio (fechamento).
- Anti-fake: **sem números mock/seed/DEMO**; 2 bugs HIGH de `0` em campo vazio.
- Fechamento pela UI **não** alcançado → F12-006 permanece **PARTIAL**.

---

## Resumo final (11 campos)

1. **Estado do projeto:** Pós-MVP 6 (UX planilha) + QA exploratório base limpa
2. **Branch/commit:** main @ ca7ec86
3. **Alembic head:** 010 (head)
4. **Porta:** 8080
5. **Testes:** pytest reset (4) + postmvp6 colunas (1); build OK; E2E manual browser 1366×768 + 1920×1080
6. **Base limpa:** sim — reset executado, 0 ordens antes, sem DEMO-* na grade
7. **QA-UI-001:** sim — ID **44**
8. **Ponto máximo:** L (fechamento bloqueado — checklist pendências)
9. **Bugs:** BLOCKER 0 · HIGH 2 · MEDIUM 4 · LOW 2 — top 3: QA-HIGH-001 (0,00 acconto), QA-HIGH-002 (0 em vazio), QA-MED-002 (persistência responsável/previsão)
10. **Arquivos atualizados:** `docs/QA_UI_E2E_BASE_LIMPA_ORDEM_REAL.md`, `CHECKLIST_MVP_IMPORTACAO_EPIC.md`
11. **Próxima etapa:** Corrigir HIGH (campo vazio → `—`); validar persistência responsável/previsão na grade; retomar E–L (embarque, aduana, LC, docs) até fechamento UI

---

## Rodada 2 — correções e reteste (2026-06-23)

**Escopo:** somente correção dos bugs HIGH/MEDIUM da Rodada 1. **Sem** reexecução do roteiro E2E A–L (Rodada 3).

### Distinção 0 vs vazio (regra de ouro)

| Campo | `null` / sem evento | `0` real |
|---|---|---|
| `total_paid` | Nenhum pagamento **liquidado** na moeda | Ao menos um pagamento liquidado; soma pode ser 0 |
| `quantity_shipped` | Nenhum `ShipmentItem` ativo | Embarque registrado com qty 0 |
| `quantity_nationalized` | Nenhum `NationalizationItem` | Nacionalização com qty 0 |
| `quantity_stocked` | Nenhum `StockEntry` | Entrada de estoque com qty 0 |

Implementação no **nível de dado** (`finance.py`, `logistics.py`, `nationalization.py`, `order_central.py`) — UI usa `formatMoney` / `emptyDash` que já tratam `null` como `—`.

### Bugs corrigidos

| ID | Veredito | Root cause | Mudança | Teste |
|---|---|---|---|---|
| QA-HIGH-001 | **FIXED** | `total_paid` sempre serializado como `"0"` quando `invoice_paid_total` somava 0 sem liquidação | `invoice_has_settled_payments()`; KPI/summary retornam `null` sem liquidação | `test_qa_high_001_total_paid_null_without_settlement`, `test_qa_high_001_total_paid_not_null_after_settlement` |
| QA-HIGH-002 | **FIXED** | `coalesce(sum(...), 0)` em cadeia de quantidades tratava “ainda não aconteceu” como zero | `_shipped/_nationalized/_stock_total_for_display()` retornam `None` sem registro | `test_qa_high_002_quantity_stages_null_before_events`, `test_qa_high_002_quantity_shipped_zero_when_shipment_exists` |
| QA-MED-002 | **FIXED** | Inputs `defaultValue` + `onBlur`; depois `onChange` em `imp` impedia save no blur | Draft local (`responsibleDraft`/`forecastDraft`) vs valor persistido em `imp` | `test_qa_med_002_003_*` + E2E `edição inline de responsável no cabeçalho` |
| QA-MED-003 | **FIXED** | Mesmo root cause do 002 na Central; API/grade já persistiam — exibição falhava | Idem MED-002 | `test_qa_med_002_003_responsible_persists_get_and_queue` |
| QA-MED-001 | **FIXED** | Submit dependia só do evento nativo `submit` do form | `handleCreate` invocado por `onClick` explícito no botão | `frontend/e2e/qa-rodada2-fixes.spec.ts` |
| QA-MED-004 | **FIXED** | `unit_price_foreign` renderizado cru da API (`12.5000`) | `formatUnitPrice()` pt-BR na aba Itens | `frontend/e2e/qa-rodada2-fixes.spec.ts` |
| QA-LOW-001 | **DEFERRED** | Labels técnicas no histórico | — | Rodada futura |
| QA-LOW-002 | **DEFERRED** | Duplicata Heroes por cliques repetidos | — | Rodada futura |

### Regressões ajustadas

- `QuantityChainResponse`: campos de quantidade aceitam `null`.
- `reconciliation.py`: pula par QTY_CHAIN quando estoque ainda não iniciado (`stocked is None`).
- `test_reconciliation_closure.py::test_close_with_approved_variance`: inclui entrada de estoque real (90) para divergência legítima.

### Evidência automatizada

| Suite | Resultado |
|---|---|
| pytest | **204 passed** (199 anteriores + **5 novos** em `tests/test_qa_rodada2_fixes.py`; 1 teste de reconciliação ajustado) |
| `npm run build` | OK |
| Playwright Rodada 2 | `frontend/e2e/qa-rodada2-fixes.spec.ts` (2 casos MED-001, MED-004) — executar com servidor ativo na Rodada 3 |

### Arquivos alterados (Rodada 2)

- Backend: `app/services/finance.py`, `order_central.py`, `logistics.py`, `nationalization.py`, `reconciliation.py`, `dashboard.py`, `closure.py`, `schemas_phase789.py`
- Frontend: `ImportationLayout.tsx`, `ImportationSectionPage.tsx`, `SuppliersPage.tsx`, `i18n/glossario.ts`
- Testes: `tests/test_qa_rodada2_fixes.py`, `tests/test_order_central.py`, `tests/test_reconciliation_closure.py`, `frontend/e2e/qa-rodada2-fixes.spec.ts`

### Próxima etapa

**Rodada 3:** E2E completo A–L em ordem nova (`QA-UI-002` ou reteste QA-UI-001 após reset), incluindo liquidação, documentos com fixture `.txt`, OCEAN→AIR, aduana, estoque, LC, conciliação, fechamento e reabertura pela UI.

---

## Rodada combinada — BLOCO 2: Nova Ordem planilha (2026-06-23)

**Escopo:** redesign do modal de abertura conforme plano `nova_ordem_planilha`; executado após BLOCO 1 (bugs QA).

### Entregas

| Item | Detalhe |
|---|---|
| Modal único | Removidas abas cadastro rápido / wizard; tela planilha `.ux-modal--wide` |
| Heroes default | `pickHeroesSupplierId` + `dedupeSuppliersByName` (QA-LOW-002 na UI) |
| Tabela itens | Qtd, preço €, desconto €, subtotal live; `create+items[]` em uma chamada |
| ProductCombobox | Autocomplete client-side por SKU/descrição |
| Totais | `parseDecimalInput` → null (mesma regra 0-vs-vazio do BLOCO 1) |
| Sem itens | Confirmação explícita antes de criar ordem vazia |
| CC preview | Pill read-only via `listBrazilAccounts`; desconto linha não cria CC |
| Financeiro | `<details>` opcional: 1 PROFORMA + 1 pagamento planejado |

### Testes

- `frontend/e2e/nova-ordem-planilha.spec.ts` — Heroes default, totais live
- `frontend/e2e/nova-ordem-regression.spec.ts` — ordem completa 2 itens → Central + grade
- `frontend/e2e/ux-postmvp6-planilha.spec.ts` — atualizado (sem abas wizard)

### Próxima etapa

**Rodada 3:** E2E operacional A–L com entrada redesenhada e bugs corrigidos — **concluída** (ver seção abaixo).

---

## Rodada 3 — E2E operacional A–L (2026-06-23)

**Escopo:** fluxo completo em base limpa, ordem **QA-UI-002**, fechamento e reabertura pela UI. Correções adicionais em conciliação QTY_CHAIN (upsert OK quando pedida=estocada).

### Ambiente

| Campo | Valor |
|---|---|
| Reset | `RESET_EPIC_TEST_DATA=1` — 17 importações removidas |
| Servidor E2E | `uvicorn` @ `127.0.0.1:8082` (build Vite atualizado) |
| Ordem | **QA-UI-002** · ID **157** |
| Estado final do teste | `REOPENED` (após fechamento + reabertura com `reason_code`) |

### Roteiro A–L (evidência Playwright)

| Bloco | Ação UI | Status | Observação |
|---|---|---|---|
| A | Nova ordem planilha → Central | **OK** | Modal único, Heroes, 2 itens (100×12,50 + 50×8) |
| B | `/itens` somente leitura | **OK** | Preços `12,50` / `8,00` |
| C | 3 faturas QA-INV-1/2/3 | **OK** | 500 + 1000 + 150 EUR |
| D | Pagamento 250 planejado + liquidar; quitar faturas | **OK** | Liquidação parcial + saldo integral |
| E | `/financeiro` da ordem | **OK** | Aba carrega |
| F | PROFORMA v1 upload `/documentos` | **OK** | v2 via API `document_key` — **LACUNA UI** reupload versionado |
| G | Embarque OCEAN → AIR | **OK** | `MODAL_CHANGE_URGENCY` |
| H | DI oficial | **OK** | Form imposto visível; registro omitido (bloquearia conciliação sem `tax_total` no doc) |
| I | Nacionalização + estoque | **PARCIAL** | Form UI visível; execução 2 SKUs + estoque via **API** — **LACUNA UI** entrada estoque |
| J | LC INITIAL + FINAL | **OK** | 2º clique UI pode gerar INITIAL duplicado — fallback API FINAL |
| K | Conciliações sem bloqueantes | **OK** | Botão fechar habilitado |
| L | Fechar → bloqueio edição → reabrir | **OK** | Bloqueio em `brazil-fields` PATCH; reabertura modal `reason_code` |

### Lacunas P0/P1 registradas

| ID | Lacuna | Prioridade |
|---|---|---|
| R3-LAC-001 | Entrada de estoque sem tela na aba aduaneiro | P1 |
| R3-LAC-002 | Versionamento documento (v2) sem UI — só API `document_key` | P1 |
| R3-LAC-003 | Nacionalização UI só 1º item; 2º SKU via API | P1 |
| R3-LAC-004 | `POST /api/invoices` não aplica `importation_guard` em ordem fechada | P1 |
| R3-LAC-005 | Botão LC 2ª versão pode enviar INITIAL se estado local desatualizado | P2 |

### Evidência automatizada

| Suite | Resultado |
|---|---|
| `frontend/e2e/qa-rodada3-e2e-completo.spec.ts` | **13 passed** (`--retries=0`) |
| pytest `test_reconciliation_closure` + `test_qa_rodada2_fixes` | **18 passed** |
| Fix | `reconciliation.py` — QTY_CHAIN atualiza para OK quando qty bate |

### Veredito Rodada 3

**PASS** — fechamento limpo pela UI alcançado; reabertura com `reason_code`; anti-fake sem DEMO/mock; lacunas documentadas onde UI ausente.

### Arquivos

- `frontend/e2e/qa-rodada3-e2e-completo.spec.ts`
- `tests/fixtures/qa-ui-doc-v1.txt`, `qa-ui-doc-v2.txt`
- `app/services/reconciliation.py` (QTY_CHAIN OK upsert)
