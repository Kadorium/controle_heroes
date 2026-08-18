# A0 — Fattura assistida → Invoice DRAFT — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | **A0** — Fattura → identificar/confirmar Order → matching de linhas → preview → **mesma** Invoice DRAFT |
| Status | **DONE** |
| Data | **2026-08-13** |
| Roadmap | **0.5.115** — elo 3 **LIGADO / PRONTO**; cadeia **3/10 = 30%** |
| Blueprint | **0.2.20** |
| Alembic | **025** (intocado) |
| Portão | **Não iniciar B0.** Próxima ação = **aguardando autorização.** |
| Preservado | Pedido **589** id **31** e **TESTE-CICLO-001** id **34** — CONFIRMED; não usados como massa destrutiva |

---

## Resposta executiva

1. A costura document-driven está fechada: Fattura → candidatos de Order → confirmação humana → linhas inequívocas ou escolha explícita → preview → **a mesma** Invoice DRAFT → Billing existente (`set_terms` / `issue` / Payables).
2. Nenhuma segunda jornada de Invoice foi criada. Issue **não** cria Payment; saldo de Payable só muda via Allocation.
3. Associação ambígua **não** é mais silenciosa: 0 Orders bloqueia; 1 sugere e exige confirmar; N lista e exige escolher; linha com `candidate_count > 1` bloqueia até `line_choices`.
4. Billing existente (create/replace/terms/issue/Payables, ADVANCE, Allocation, G2–G5, FIN-3B, FIN-4) foi **reutilizado**, não reimplementado.

---

## Estado inicial (F0) — Planning **confirmado**

F0 correu **sem código**. Branch `main`, runtime Ricardo `:8081` / `epic_v2`, Alembic 025. Sem reset.

| Hipótese | Resultado |
|---|---|
| Caminho B já existe (Order CONFIRMED → Invoice DRAFT → qty/terms → issue → Payable) | **Confirmada** na UI — não reconstruir |
| Caminho A existia, mas `order_id` era digitado; `candidate_count > 1` fazia auto-pick `fitting[0]` | **Confirmada** — estes eram os gaps A0 |
| Capacidades Billing/G2–G5/FIN-3B/FIN-4/ADVANCE funcionam | **Confirmadas** como reuso/regressão |
| Refutação de owner, arquitetura ou migration | **Não houve** — execução F1–F5 seguiu |

### Caminho B (não reconstruído)

Runtime `:8081`. Abri pedido CONFIRMED dedicado (não 31/34) → painel de faturas. Vi criar Invoice DRAFT. Cliquei editar qty, gravar terms, Emitir (documento anexado **API**). Resultado: Invoice ISSUED + Payables OPEN. Fluxo = `OrderInvoicesPanel` + `InvoiceDetailPage` existentes.

### Caminho A (antes de A0)

Runtime `:8081`. Abri Fattura ingerida. Vi Policy A e campo numérico `order_id` obrigatório — **sem** lista de candidatos. Preview com `order_id` mostrava linhas; ambiguidade virava warning e commit seguia na primeira candidata. Após commit, a Invoice era a DRAFT Billing já existente.

### Gaps confirmados

- Sem mecanismo de candidatos 0/1/N.
- Auto-pick de linha ambígua.
- Scadenze extraídas (`due_date_iso`) não apareciam no painel estruturado (`s.date`) — correção **localizada** de binding, necessária ao gate A0.

---

## Alterações

### Candidatos de Order (F1) — DEC-A0-ORDER-CANDIDATES

Filtros determinísticos em `fattura_order_candidates.py`, via `orders.public` + `billing.public.order_qty_availability`. Sinais: `supplier_id_catalog` único (ignora AMBIGUOUS/ausente), cobertura G4 de todas as linhas PDF (`product_id` / `sku_snapshot` / `external_code`), residual ISSUED, moeda como exclusão fraca. **Nunca** `supplier + invoice_number`. Sem DDT/data/total como identidade.

| Candidatos | Comportamento |
|---|---|
| 0 | Não inventa Order; bloqueia commit; explica |
| 1 | Sugestão forte; operador confirma; commit envia `order_id` explícito; sem auto-commit |
| N | Lista com evidências; operador escolhe |

GET HTTP `/orders` **não** ganhou filtro; a leitura filtrada é contrato Python público.

### Ambiguidade de linha (F2) — DEC-A0-AMBIGUOUS

`plan_fattura_lines(..., line_choices)`. `len(fitting)==1` casa; `len(fitting)>1` → `fattura_line_ambiguous` até `{row_index, order_item_id}`. Commit **não** usa `fitting[0]`. Preço divergente = warning FIN-3B (fatura segue o documento), não identidade. G2–G5 / COMMITMENT / `external_code` reutilizados.

### UI (F3)

`FatturaCommitPanel`: documento, candidatos + evidências, confirmar pedido, linhas casadas/ambíguas/sem match, qty/preço, scadenze, blockers, o que será criado. Após commit: link da **Invoice Detail existente**. Nenhuma tela Billing nova.

Correção localizada: `FatturaStructuredPanel` passa a mostrar `due_date_iso \|\| date`.

### Fora de A0 (intocado)

B0, picker/residual da Invoice manual, ADV-S, PaymentOrder, auto-allocation, ACCONTO, cronograma→PaymentTerm, parser Ordine, 3A/020, J#5-REC, J#6, settlement CUSTOMS_FUNDING, nova entidade Invoice/Payable, migration.

---

## Gates

| Gate | Resultado |
|---|---|
| Testes A0 | `test_orders_a0_fattura_assist.py` — 0/1/N, supplier ausente/ambíguo, SKU discrimina, ISSUED esgotado, linha única/múltipla/escolha/sem candidato, COMMITMENT, mesmo preço dois buckets, commit DRAFT + issue Payables, contratos públicos |
| Regressão FIN-3B | Preview ambíguo agora `can_commit False` até `line_choices`; 244 dois buckets envia escolhas explícitas |
| Suíte | pytest **545 passed**; Vitest `FatturaCommitPanel` **2 passed**; `check:api-drift` **PASS** |
| Arquitetura | Ingestion → públicos Orders/Billing; Orders ↛ Billing; sem ciclo novo; V2 ↛ V1; suffixes internos no `module_graph` |
| UI real | F5 abaixo — 4 casos |

---

## F5 — aceite na UI real

Amostra dedicada (**API** seed: `docs/v2/etapa-j4-fin/logs/a0_f5_seed.py`). PDF = `Fattura_244.pdf` (documento real Heroes). Números de fatura corrigidos para não colidir com `244`. Pedidos 31/34 **não** tocados.

### Caso 1 — um candidato

Runtime `:8081`. Abri `/ingestion/33`. Vi sugestão forte **#39 A0-F5-ONE**, scadenze 20/04/2026 e 30/06/2026, commit desabilitado. Cliquei rádio 39 → Confirmar este pedido. Preview: 2 linhas casadas, qty 50+150 @ 99,83, `can_commit` sim. Cliquei Commit. Resultado: **SUCCEEDED** → Invoice **#31** DRAFT no pedido 39 (`create_invoice` / `set_terms` / `link_document`). **API:** SKU isolado para obter candidato único (não usar 31/34).

### Caso 2 — N Orders

Runtime `:8081`. Abri `/ingestion/34` (EAN original do PDF). Vi **“4 pedidos possíveis. O sistema não escolhe em silêncio.”** (42, 41, 40, 38 — **não** 31/34). Commit desabilitado. Cliquei **#40 A0-F5-N1** → Confirmar. Cliquei Commit. Resultado: **SUCCEEDED** → Invoice **#32** DRAFT no pedido **40** (não 38/31/34).

### Caso 3 — linha ambígua

Runtime `:8081`. Abri `/ingestion/35`. Vi N candidatos; escolhi **#42 A0-F5-AMB**. Preview: linhas ambíguas; commit bloqueado (`fattura_line_ambiguous`). Cliquei item **#55** (linha 0) e **#56** (linha 1). Preview passou (`Casadas: 2`, `can_commit` sim). Cliquei Commit. Resultado: **SUCCEEDED** → Invoice **#33** DRAFT no pedido **42**.

### Caso 4 — downstream existente (não é entrega nova)

Runtime `:8081`. Abri `/invoices/31` (DRAFT do caso 1; documento já era `Fattura_244.pdf` via `link_document` — **sem** attach extra). Vi terms das scadenze, qty/preço da Fattura. Cliquei **Emitir** (sem “sem documento”). Resultado: status **Emitida**; obrigações 5.000 + 14.966 OPEN, saldo = valor. Abri fila AP e `/payables/31/fx`: Payable OPEN; **“Não é aplicado automaticamente”**; **zero** Allocation nos Payables 31/32. Nenhum Payment criado pelo issue.

### Atritos UX (registrados, **não** corrigidos)

- Confirmar pedido é dois passos (rádio + botão).
- Radios Policy A/B/C1/C2 continuam ruidosos.
- JSON técnico das linhas IR ainda visível.
- Caso 2 lista também o pedido AMB se o residual cobre — correto pelo filtro, barulhento.
- Após escolher a linha 0, a linha 1 continua exigindo escolha (correto; a UI não “consome” em silêncio).

---

## Provas pedidas

| Afirmação | Evidência |
|---|---|
| Billing existente reutilizado | Commit chama `create_invoice` / `set_terms` / `link_document`; caso 4 usa `InvoiceDetailPage` Emitir → `_generate_payables` |
| Nenhuma segunda jornada | Sem entidade/tela/rota nova de Invoice; OpenAPI só estendeu preview/commit Ingestion |
| Nenhuma associação ambígua silenciosa | Casos 2 e 3: commit disabled até escolha; teste inverte `can_commit` em ambiguidade |

---

## Roadmap / Blueprint / Alembic

| Item | Valor |
|---|---|
| Roadmap final | **0.5.115** |
| Elo 3 | **PRONTO / LIGADO** — Fattura real 244 exercitada até Invoice; issue→Payable no caso 4 |
| Cadeia n/d | **d 10→10** (inalterado); **n 2→3**; **% 20→30** — motivo: elo 3 PRONTO. Ingestão 2/7 **inalterada** (aceite da família Fattura ainda não é o aceite J#3 completo) |
| Próxima ação | **Aguardando autorização.** Não iniciar B0 |
| Blueprint | **0.2.20** — invariantes 0/1/N e blocker de linha; §7.18; não há evidência operacional no Blueprint |
| Alembic | **025** |

Livro-razão: Financeiro 5/5 **não** conta Billing pré-existente como entrega nova de A0.

---

## Pendências

- B0 (picker/residual da Invoice manual) — **não autorizado**.
- Elo 4 FRÁGIL: quitação crédito+saldo não exercitada no mesmo pedido da Fattura A0.
- Aceite pleno das outras famílias de documento (Ingestão 2/7).
- Atritos UX acima.

## Próxima etapa lógica

Aguardar autorização. Candidato natural da cadeia (não iniciado): **B0** ou o incremento que o advisor escolher para o elo 4. **Este turno não começa nenhum.**

## Recomendação

Aceitar A0 **DONE**. Ratificações DEC-A0-ORDER-CANDIDATES e DEC-A0-AMBIGUOUS já estão no Blueprint 0.2.20.

---

## Arquivos relevantes (produto)

- `v2/app/ingestion/fattura_order_candidates.py` (novo)
- `v2/app/ingestion/fattura_line_match.py`
- `v2/app/ingestion/fattura_commit_commands.py` + `schemas.py` + `routes.py`
- `v2/app/orders/public.py` / `queries.py` / `repository.py` (`list_orders` + `supplier_id`)
- `v2/app/foundation/module_graph.py`
- `v2/frontend/src/features/ingestion/FatturaCommitPanel.tsx` (+ test)
- `v2/frontend/src/features/ingestion/FatturaStructuredPanel.tsx`
- `v2/tests/test_orders_a0_fattura_assist.py` (novo)
- `v2/tests/test_j4_fin3b.py`, `test_j4_fin23.py`

Evidência interna (não listar item a item ao advisor): `docs/v2/etapa-j4-fin/logs/` (`a0_f0_*`, `a0_f5_seed.py`, `a0_f5_verify.py`).

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md; docs/v2/etapa-j4-fin/J4_BILLING_CAPACITY_ADVISOR_HANDOFF.md
- Evidence: docs/v2/etapa-j4-fin/
- Roadmap status: 0.5.114 → 0.5.115; A0 DONE; elo 3 FRÁGIL → PRONTO; cadeia 2/10 (20%) → 3/10 (30%)
- Next TODO: aguardando autorização (não B0)
- Return to advisor: docs/v2/etapa-j4-fin/J4_BILLING_CAPACITY_ADVISOR_HANDOFF.md
```
