# EPIC Controle — Análise de Reconstrução e Roadmap V2

> **Natureza deste documento.** Fonte operacional da reconstrução V2: fases, status, gates, ADRs, evidências e bloqueios. O **destino** funcional/arquitetural está em [`docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md`](docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md). Índice: [`docs/README.md`](docs/README.md).
>
> **Convenção de rótulos.** `[FATO]` = comprovado por execução/leitura. `[INFERÊNCIA]` = interpretação sustentada por evidência. `[HIPÓTESE]` = ainda não validada. `[DECISÃO]` = decisão vigente.

### Cabeçalho de sincronização documental

| Campo | Valor |
|---|---|
| Versão / revisão documental | **0.5.6** — Inc-4A+4B FX três visões **DONE** |
| Última atualização material | **2026-07-23** |
| Fase atual | **Order-to-Pay (J#2)** — **IN_PROGRESS** · Inc-1…**Inc-4 DONE**; próxima **Inc-5** |
| Última fase concluída | **Inc-4 — FX (três visões) = 4A+4B** |
| Próxima fase | **Inc-5** — Fila AP + cockpit Reporting (§O.5) |
| Working tree relevante | Fundação+Inc-1…Inc-4 **uncommitted** em `main` @ `008fb49` |
| Commit / checkpoint de referência | Tip: `008fb49` · Checkpoint pré-Fundação: `checkpoint/pre-foundation` @ `7d7f398` |
| Blueprint canônico | **v0.2.4** — três visões FX; ownership Treasury |

### Painel executivo de progresso

Visão curta do progresso V2. Detalhes técnicos, gates e comandos: §J / §N / §O.

| Fase / incremento | Objetivo | Status | Última evidência | Próximo passo | Bloqueio relevante |
|---|---|---|---|---|---|
| 0B — Contrato | Roadmap + Blueprint aprovados | **DONE** | 2026-07-22 APPROVED | — | — |
| Fundação | Layout `v1/`+`v2/`; Identity/Audit/Documents; harness | **DONE** | Gates §N verdes (WIP) | — | — |
| Inc-1 Catalog + Orders | Supplier/Product; Order DRAFT→CONFIRM/CANCEL | **DONE** | Gates O.1 (§O.1) | — | — |
| Inc-2 Billing + Payables | Invoice + Terms → Payables; sconto | **DONE** | Gates O.2 (§O.2); DEC-SCONTO-ITEM fechada | — | — |
| Inc-3 Payment + Allocation | Payment; alocação em Payable | **DONE** | Gates O.3 (§O.3) | — | — |
| Inc-4 FX (4A+4B) | Três visões; plan/quote/execution | **DONE** | §O.4 gates 2026-07-23 | Inc-5 | — |
| Inc-5 Fila AP + cockpit | Fila AP; cockpit via Reporting | **TODO** | Plano §O.5 | Após Inc-4 DONE | — |
| Inc-6 E2E/goldens/aceite | E2E; equivalência `parse_it`; DoD J#2 | **TODO** | Plano §O.6 | Após Inc-5 | — |
| Ingestão | Adapters + contrato canônico | **TODO** | §J#3 | Após Order-to-Pay | — |
| Logística | Shipment + PackingList | **TODO** | §J#4 | Após Ingestão | — |
| Aduana + Inventory | ImportProcess 1:N; estoque | **TODO** | §J#5 | Após Logística | — |
| Costing/Reconciliation | Landed cost + pares | **TODO** | §J#6 | Após Aduana | — |
| Dashboard | Read models | **TODO** | §J#7 | Após Costing | — |
| Aceite final | SC-* + arquivar V1 | **TODO** | §J#8 | Após Dashboard | — |

### Precedência interna deste Roadmap `[DECISÃO]`

Não há “trecho antigo vence trecho novo”. Em caso de aparente conflito **dentro deste arquivo**, usar esta ordem de autoridade por assunto:

| Assunto | Fonte canônica **neste** Roadmap | Não usar como estado atual |
|---|---|---|
| Produto / arquitetura-alvo / aceite | **Blueprint V2** (fora deste arquivo) | A–E como se fossem destino |
| ADRs vigentes | **§M.1** | Inferências pré-ADR em A–E |
| Fases e status atuais | **§J** | Narrativa de diagnóstico em A–E/B.1–B.2 |
| Próxima ação autorizada | **§L** (+ plano §O) | Gates históricos já superados |
| Evidências da Fundação | **§N** (+ baselines em §M.0) | Qualquer frase pré-Fundação que diga o contrário |
| Diagnóstico / baseline histórico | **§A–E** e **§B.1–B.2** | Como se descrevessem o layout ou status de hoje |

**Regra anti-regressão documental:** texto marcado como pré-Fundação / histórico / diagnóstico **nunca** prevalece sobre §B.0, §I, §J, §L, §M.0 ou §N.

### Autoridade documental por assunto `[DECISÃO]`

| Assunto | Canônico |
|---|---|
| Produto, comportamento, telas, fluxos, aceite, modularidade-alvo | Blueprint V2 |
| Fases, status, gates, ADRs, evidências, bloqueios | Este Roadmap (§J / §M.1 / §N / §L conforme acima) |
| Método de investigação e implementação no código/docs V2 | `.cursor/rules` V2 (+ router global) |
| Legado V1 | `docs/v1/README.md` (histórico arquivado) + monólito em `v1/` |
| Runtime | Código real (inspecionar) |

**Checklist V1 ≠ DoD V2.**

---

## Sumário

- [A. Veredito executivo](#a-veredito-executivo)
- [B. Estado comprovado (atual + baselines históricos)](#b-estado-atual-comprovado)
- [C. Confirmação/refutação das hipóteses](#c-hipoteses)
- [D. Matriz de reaproveitamento](#d-matriz-de-reaproveitamento)
- [E. Matriz comparativa das três estratégias](#e-matriz-comparativa)
- [F. Arquitetura-alvo (canônica)](#f-arquitetura-alvo)
  - [F.1–F.8 Ownership, modelo, telas, slice — detalhe no Blueprint](#f-arquitetura-alvo)
- [G. Arquitetura da nova importação](#g-nova-importacao)
- [H. Estratégia de banco (sem migração de dados)](#h-banco)
- [I. Layout do repositório e transição](#i-transicao)
- [J. Roadmap executável (único)](#j-roadmap)
- [K. Riscos](#k-riscos)
- [L. Próxima etapa lógica](#l-proxima-etapa)
- [M. Governança V2](#m-governanca)
- [N. Fundação técnica (executada)](#n-fundacao)
- [O. Execução Order-to-Pay — Inc-1, Inc-2 e Inc-3 concluídos](#o-order-to-pay-plan)
  - [O.1 Inc-1 — Catalog mínimo + Orders](#o-order-to-pay-plan)
  - [O.2 Inc-2 — Billing + Payables](#o-order-to-pay-plan)
  - [O.3 Inc-3 — Payment + PaymentAllocation](#o-order-to-pay-plan)
  - [O.4 Inc-4 — FX mínimo + Documents + Audit](#o-order-to-pay-plan)
  - [O.5 Inc-5 — Fila AP + cockpit via Reporting](#o-order-to-pay-plan)
  - [O.6 Inc-6 — E2E, walkthrough, goldens e aceite](#o-order-to-pay-plan)
- [Apêndice — Evidências](#apendice-evidencias)

---

<a id="a-veredito-executivo"></a>
## A. Veredito executivo

**Recomendação primária: `[DECISÃO]` Alternativa B — Reconstrução modular com reaproveitamento seletivo.** Reescrever modelo, fronteiras, APIs, UI e pipeline de ingestão; **portar com testes** os cálculos validados (financeiro, câmbio/PnL, landed cost, conciliação) e o parser Heroes (como adapter).

**Segunda melhor: Alternativa C.** Viável porque **nenhum dado precisa ser migrado** (premissa definitiva abaixo), mas desperdiça ~4.000 linhas de lógica já testada.

**Alternativa A — evolução — desaconselhada.** O modelo V1 usa a ordem como contêiner (`importation_id` em quase tudo); um Numerário de teste prova **1 DUIMP → N faturas** — o esquema V1 não representa isso.

### Premissa definitiva de dados `[DECISÃO]`

**Todo o conteúdo atual do workspace é exclusivamente de teste e integralmente descartável:**

- banco `epic_importacao` (incluindo registros com aparência operacional);
- backups SQL e de anexos;
- anexos, planilhas, PDFs e ZIPs;
- massa `DEMO-*` / `QA-*` / `E2E*`;
- ordens, faturas, pagamentos e usuários atuais.

**Não há dado produtivo a preservar, migrar, reconciliar ou reconstruir.**

Consequências:

| O quê | Decisão |
|---|---|
| Banco V2 | Começa **vazio** (`epic_v2`) |
| Massa de teste V2 | **Determinística** (seeds/fixtures versionados) |
| PDFs / planilhas atuais | **Fixtures / golden files** — não são fontes oficiais de produção |
| Comparação V1↔V2 | Apenas **comportamento, contratos e cálculos** |
| Migração de linhas V1→V2 | **Nenhuma** |
| Conciliação de registros no “corte” | **Não se aplica** |
| Inspeção de backups SQL para migração | **Não se aplica** |

### Layout de repositório `[DECISÃO]` (ADR-04 / ADR-13)

```text
root/
├── .git/
├── .gitignore
├── .cursor/                 # router + rules V1/V2 (split feito na Fundação)
├── docs/                    # documentação consolidada
├── ROADMAP_V2_EPIC.md       # este arquivo (fonte operacional V2)
├── v1/                      # monólito legado (consulta + goldens)
└── v2/                      # app novo (Fundação+; Order-to-Pay em diante)
```

**Layout-alvo (ADR-04/13) — status de execução:** materializado na Fundação (`DONE` no working tree). Ver estado atual em §B.0 / §I / §N — **não** há pendência de “layout inicial não executado”.

**Política Git:** autoridade única em [`.cursor/rules/epic-project-router.mdc`](.cursor/rules/epic-project-router.mdc) — trabalhar em `main`; commits/branches só com pedido explícito; nunca descartar WIP.

---

<a id="b-estado-atual-comprovado"></a>
## B. Estado comprovado

### Linha do tempo de baselines (ler nesta ordem)

| Marco | Onde | O que descreve |
|---|---|---|
| Diagnóstico / baseline inicial | §B.1–B.2, §A–E | Monólito **na raiz**; motivação da Alt. B — **histórico** |
| Checkpoint pré-move | §M.0 (pré-move) | SHA `7d7f398` antes do move — **histórico** |
| Pós-move V1 | §M.0 (pós-move) + §N.2–N.5 | Monólito em `v1/`; sem regressão de path — **histórico da Fundação** |
| **Estado atual V2** | **§B.0**, §I, §J, §L, §N, painel executivo | Layout `v1/`+`v2/`; Fundação **DONE**; Order-to-Pay **IN_PROGRESS** (Inc-1/2/3 DONE) |

### B.0 Estado atual pós-Fundação `[FATO]` (2026-07-22) — **autoridade de “como está hoje”**

| Item | Valor |
|---|---|
| Layout | `root/{.git,.cursor,docs,ROADMAP,README,v1,v2}` — **sem** `app/`/`frontend/` na raiz |
| Branch ativa | **`main`** @ `008fb49` (origin/main) |
| Checkpoint segurança | `checkpoint/pre-foundation` @ `7d7f398` (preservada) |
| Working tree | Fundação + Inc-1 + Inc-2 + Inc-3 **DONE e não commitados** sobre `main` (política: sem commit automático; commit **não** é gate) |
| V1 | Monólito em `v1/` — porta **8080**, banco `epic_importacao` |
| V2 | App em `v2/` — porta **8081**, bancos `epic_v2` / `epic_v2_test` · módulos: `foundation`, `identity`, `audit`, `documents`, `catalog`, `orders`, `billing`, `treasury` |
| Orders / Billing / Treasury | Catalog + Orders (**Inc-1 DONE**); Billing + Payables (**Inc-2 DONE**); Treasury/Payment (**Inc-3 DONE**) |
| Docs | `docs/v2/BLUEPRINT_*` **v0.2.3** canônico; histórico em `docs/v1/` |
| Cursor | Router global + V1 `v1/**,docs/v1/**` + V2 `v2/**,docs/v2/**,ROADMAP,docs/README.md` |
| Harness / goldens | **DONE** — goldens `parse_it_*` + testes de schema/presença; equivalência de cálculo = fase Order-to-Pay (§O Inc-6), **não** gate da Fundação |

### B.1 Baseline histórico pré-Fundação `[FATO]` (diagnóstico — **não é estado atual**)

> Snapshot do monólito **ainda na raiz**, antes do move. Baseline de comparação apenas. Qualquer leitor que precise do layout de hoje deve usar **§B.0**.

- Monólito na raiz (à época): SPA React + FastAPI `/api`, porta **8080**; PostgreSQL `localhost:5433/epic_importacao`.
- `ROOT_DIR` = pai de `app/` (então a raiz do repo) — **obsoleto** após o move; hoje o monólito vive sob `v1/`.
- Python 3.10.11, Node 22.18, Alembic `001`→`014 (head)`.

### B.2 Validações dinâmicas históricas `[FATO]` (pré-Fundação / diagnóstico — **não é gate atual**)

| Verificação | Resultado (pré-Fundação / diagnóstico) |
|---|---|
| `pytest -q` | 31 falharam / 294 passaram / 1 skip (depois alinhado a 30f/294p/2s no checkpoint) |
| `tsc --noEmit` | ~28 erros |
| `vite build` | Passa (sem type-check) |
| Vitest / Playwright | 47p/1f · 27p/18f/11 blocked |
| Alembic | `014 (head)` |

Baselines oficiais pré×pós-move e evidências da Fundação: §M.0 / §N. Status de fase: §J.

### B.3 Dados — inventário e tratamento `[FATO]` + `[DECISÃO]`

Inventário histórico (amostra na época do diagnóstico): usuários, fornecedores, produtos, ordens, faturas, etc. em `epic_importacao`; fixtures sob `v1/tests/` após o move.

**Tratamento `[DECISÃO]`:** tudo descartável. A V2 **não** importa esses registros. Documentos selecionados → `v2/tests/fixtures/source_documents/`.

### B.4–B.7 Arquitetura V1 (histórica)

Ordem-hub, ciclos por import local, `order_central` mega-agregador, FE estruturalmente a reescrever — motivação da Alt. B. Código legado agora em `v1/`.

---

<a id="c-hipoteses"></a>
## C. Confirmação/refutação das hipóteses

| # | Hipótese | Conclusão |
|---|---|---|
| 1–7 | Ordem-contêiner; módulos autônomos; cockpit; FE/BE por tela; ingestão multi-documento | **Confirmadas** `[FATO]` |
| 8 | Reescrever mais simples que evoluir | **Confirmada** `[DECISÃO]` — zero migração de dados + FE descartável + Alt. B para preservar calculadores |

---

<a id="d-matriz-de-reaproveitamento"></a>
## D. Matriz de reaproveitamento

| Componente | Classificação | Destino |
|---|---|---|
| Enums / RBAC | **PORT_WITH_REVIEW** | Identity / vocabulário V2 |
| finance, fx_pnl, landed_cost, reconciliation | **PORT_WITH_TESTS** | Billing / Treasury / Costing / Reconciliation |
| Parser Heroes | **PORT_WITH_TESTS** | Ingestion (adapter) |
| Commit Heroes / ORM / routers / FE / api.ts / order_central | **REWRITE** / **RETIRE** | V2 limpa |
| Attachments / audit | **PORT_WITH_TESTS** | Documents / Audit |
| Scripts start/backup | **PORT_WITH_TESTS** | `v1/scripts` + novos em `v2/scripts` |
| Documentos de teste (PDFs/XLSX selecionados) | **PORT_WITH_TESTS** | Fixtures V2 (cópia seletiva) |
| Adapters PDF | **REWRITE (novo)** | Ingestion |

---

<a id="e-matriz-comparativa"></a>
## E. Matriz comparativa

Totais ponderados: **A ≈ 171 · B ≈ 316 · C ≈ 304**. `[DECISÃO]` **B**. Critério “migração de dados” favorece B e C igualmente (custo zero de dados).

---

<a id="f-arquitetura-alvo"></a>
## F. Arquitetura-alvo (canônica)

`[DECISÃO]` Monólito modular em **`v2/`** (FastAPI + SQLAlchemy + Postgres + React/Vite). Sem Docker/microservices/cloud.

**Detalhe normativo de módulos, entidades, telas, fluxos e manutenibilidade:** Blueprint §§3, 5, 6, 8, 13. Abaixo permanece o resumo operacional vinculado aos ADRs.

### F.1 Ownership e dependências (resumo)

Dependências de pacote (semântica Blueprint §5.16: `A --> B` = A depende da API pública de B): **Billing → Orders → Catalog**; **Treasury → Billing**; agregados **Order** | **Shipment** | **ImportProcess/DUIMP**. UI “Financeiro” une Billing+Treasury.

| Módulo | Possui | Proibido depender de |
|---|---|---|
| Orders | Order, OrderItem, termos comerciais | Billing, Treasury, Logistics, Customs, Costing |
| Billing | Proforma, Invoice, InvoiceItem, PaymentTerms, Payable | Treasury, Logistics, Customs |
| Treasury | Payment, PaymentAllocation, FX, Credit, Discount, BrazilCurrentAccount | Orders (direto), Logistics, Customs |
| Logistics | Shipment, ShipmentItem | Billing, Treasury, Costing |
| Customs | ImportProcess, CustomsDocument, Tax, Nationalization | Treasury |
| Inventory | InventoryMovement, EntrepostoMovement | Billing, Treasury |
| **Costing** | **Expense**, LandedCostVersion, components | Reporting (escrita) |
| Demais | Identity, Audit, Documents, Catalog, Ingestion, Reconciliation, Reporting, Foundation | Reporting não escreve domínio |

**Expense** = Costing. Tax = Customs. Modularidade interna: **ADR-14** + Blueprint §3.2 / §13.4.

### F.2–F.6 Modelo (ponte)

- Liquidação só via Payable; antecipo não alocado não reduz saldo (ADR-06).
- DUIMP → Invoice 1:N; Shipment sem `order_id` (ADR-12).
- Estados por agregado (ADR-09); `StockBalance` derivado (ADR-07); `document_links` em Documents (ADR-08).
- Pendências: DEC-DUIMP-MULTI-SHIP, DEC-ENDERECO; L-001, L-003.
- Especificação completa: Blueprint §6.

### F.7 Telas (ponte)

Financeiro, Ordens/cockpit, Ingestão, Logística, Aduana, Inventory, Costing/Reconciliation, Dashboard por último. Detalhe: Blueprint §8. Cockpit = read model (não `order_central`).

### F.8 Order-to-Pay (1º slice)

Order → Invoice+PaymentTerms → Payable → Payment+Allocation → FX → Document+Audit → fila → cockpit. Fixture: `Fattura_181` (acconti). Ingestão completa não é pré-requisito. Aceite: Blueprint SC-01… e §7 correlatos.

---

<a id="g-nova-importacao"></a>
## G. Arquitetura da nova importação

Pipeline: arquivo → identificação → hash imutável → adapter → contrato canônico → staging → revisão → commit idempotente → objeto operacional.

**Documentos de teste / golden files** (não “fontes de produção”):

| Fixture representativa | Destino de domínio | Extração? |
|---|---|---|
| Ordine PDF | Orders | Sim |
| Fattura / Fattura con acconti | Billing | Sim |
| FatturaDoganale | Customs | Sim |
| PackingList | Logistics | Sim |
| PrintDeclaration | Documents only | Não |
| Solicitação de Numerário | Customs + Costing | Sim (1 DUIMP → N invoices) |
| Heroes XLSX | Orders/Billing via adapter | Sim |

Cada fixture em `v2/tests/fixtures/source_documents/` deve ter **cenário + resultado esperado** documentados. Cópia **seletiva**, não indiscriminada.

---

<a id="h-banco"></a>
## H. Estratégia de banco (sem migração de dados)

`[DECISÃO]`

1. Novo banco **`epic_v2`**, schema novo (Alembic próprio em `v2/`).
2. **V2 começa vazia.**
3. Massa de teste = seeds/fixtures **determinísticos** versionados no repositório.
4. **Nenhum** dado de `epic_importacao`, backups SQL ou anexos V1 é migrado.
5. Comparação V1↔V2 = **comportamento / contratos / cálculos** (caracterização + equivalência), nunca inventário de linhas.
6. Backups SQL V1: podem permanecer arquivados em `v1/backups/` por curiosidade histórica; **não** entram no plano de migração nem exigem inspeção para go-live.
7. Mapeamento mental V1→V2 (só para portar regras): `importation_orders` → Order + ImportProcess; invoices → Billing; payments → Treasury; etc. — **não** script de ETL.

---

<a id="i-transicao"></a>
## I. Layout do repositório (pós-Fundação)

### I.1 Layout atual `[FATO]`

```text
root/
├── .git/
├── .gitignore
├── .cursor/                      # router + rules V1/V2
├── docs/
│   ├── README.md                 # índice canônico
│   ├── v2/BLUEPRINT_SISTEMA_EPIC_V2.md
│   └── v1/                       # histórico: *_V1.md, CURSOR_RULES_*, archive/
├── ROADMAP_V2_EPIC.md
├── README.md
├── v1/                           # monólito legado executável
└── v2/                           # monólito modular (Foundation+)
```

### I.2 Raiz

`.git`, `.gitignore`, `.cursor/`, `docs/`, `ROADMAP_V2_EPIC.md`, `README.md`. Sem `.env`/`.venv` compartilhados.

### I.3 V1 (`v1/`)

Monólito completo executável (app, frontend, alembic, tests, scripts, data, backups, bats, `.env`). Referência de comportamento e goldens.

### I.4 Fixtures

Em `v1/tests/**`; cópias seletivas em `v2/tests/fixtures/source_documents/`.

### I.5 `.env`, `.venv`, Cursor Rules `[DECISÃO]` / `[FATO]`

| Item | Estado atual |
|---|---|
| `.env` | `v1/.env` e `v2/.env` separados |
| Bancos | `epic_importacao` (V1) · `epic_v2` / `epic_v2_test` (V2) |
| Portas | V1 **8080** · V2 **8081** |
| Dependências | Isoladas (`v1/.venv`, `v2/.venv`, node_modules por app) |
| Cursor | Router global; V1 `v1/**,docs/v1/**`; V2 `v2/**,docs/v2/**,ROADMAP,docs/README.md` |
| Git | Política em `epic-project-router.mdc` — `main` default; sem commit automático |

### I.6 Comparação V1↔V2

Caracterização / equivalência de cálculos e contratos — **sem** reconciliação de linhas de banco.

---

<a id="j-roadmap"></a>
## J. Roadmap executável (único)

| # | Fase | Objetivo | Blueprint | Gate de saída |
|---|---|---|---|---|
| 0 | **0B — Contrato** | Roadmap + Blueprint | §§1–17 | **DONE / APPROVED** (2026-07-22) |
| 1 | **Fundação técnica** | Move `v1/`, scaffold `v2/`, Identity/Audit/Documents, OpenAPI+client, `epic_v2` vazio, harness/goldens de caracterização, **modularidade** | §§5.1–5.4, 11, 13.4; REQ-V2-MOD-001 | **DONE no working tree** (código + gates §N; commit **não** exigido) |
| 2 | **Order-to-Pay** | Orders + Billing + Treasury (F.8); equivalência `parse_it` vs golden | §§5.6–5.8, 7.1–7.6, 8.3–8.13 | **IN_PROGRESS** — Inc-1/2/3 **DONE**; Inc-4 **NOT_STARTED**; aceite F.8 + DoD (§O) |
| 3 | **Ingestão documental** | Contrato canônico + adapters + fixtures | §§5.9, 7.2, 10 | Golden files + commit idempotente |
| 4 | **Logística** | Shipment + PackingList | §§5.10, 7.7–7.8 | DoD |
| 5 | **Aduana/DUIMP + Inventory** | ImportProcess 1:N + StockBalance | §§5.11–5.12, 7.9–7.11 | DoD com fixture Numerário |
| 6 | **Costing/Reconciliation** | Expense + landed cost + pares | §§5.13–5.14, 7.12–7.16, 9 | Equivalência de **cálculo** vs V1 |
| 7 | **Dashboard** | Read models | §§5.15, 8.2, 12 | DoD |
| 8 | **Aceite final e arquivamento V1** | Cenários + equivalência + arquivar V1 | §15 SC-* | V2 aceita; V1 arquivada |

> Fase 8 **substitui** “Corte da V1 com conciliação de registros”.

---

<a id="k-riscos"></a>
## K. Riscos

| Risco | Mitigação |
|---|---|
| Regressão ao portar cálculo | Caracterização + equivalência (comportamento) |
| Layout PDF/XLSX instável | Adapters versionados + fixtures + revisão humana |
| Move `v1/` quebrar paths | Mitigado na Fundação (§N): baseline pós-move = pré-move; sem regressão |
| `.venv` com path absoluto | Recriar ambientes |
| Reescrita horizontal | Fatias verticais + DoD |
| L-001 / L-003 | Hipótese provisória; isolar na fase |

---

<a id="l-proxima-etapa"></a>
## L. Próxima etapa lógica

**Próxima etapa:** revisar e executar **Inc-4 — FX mínimo + Documents + Audit**.

**Contexto `[FATO]`:** 0B = DONE/APPROVED · Fundação = DONE · Inc-1/2/3 = DONE · Order-to-Pay = **IN_PROGRESS** · Inc-4 = **NOT_STARTED** · WIP em `main` @ `008fb49` (sem commit até pedido explícito) · checkpoint `7d7f398` preservada.

Gates de Inc-1/2/3 e DEC-SCONTO-ITEM estão **superados** — não são bloqueios atuais.

---

<a id="m-governanca"></a>
## M. Governança V2

### M.0 Estado

`0B APPROVED · Fundação J#1 DONE no working tree · Inc-1/2/3 DONE · Order-to-Pay J#2 IN_PROGRESS (Inc-4 NOT_STARTED) · checkpoint/pre-foundation @ 7d7f398 preservada · Blueprint v0.2.3.`

#### Git — normalização pós-Fundação (2026-07-22) `[FATO]`

| Item | Valor |
|---|---|
| Procedimento | `git symbolic-ref HEAD refs/heads/main` + `git reset` (índice); working tree **intacto** |
| Branch **ativa** / HEAD | **`main`** @ `008fb49` (= `origin/main`) |
| Checkpoint | `checkpoint/pre-foundation` @ `7d7f398` **preservada** — **não** é o HEAD atual |
| Commits novos | **Nenhum** (política: sem commits/branches automáticos) |
| WIP | Fundação + Inc-1 + Inc-2 + Inc-3 + reorg + docs permanecem **uncommitted** sobre `main` |
| Política | `.cursor/rules/epic-project-router.mdc` — main default; commit só sob pedido |
| Gate de fase | Fundação = **DONE** independentemente de commit |

**Leitura dos diffs (sem alterar estado):** `git diff --stat main` = checkpoint + Fundação + posteriores; `git diff --stat checkpoint/pre-foundation` = Fundação + posteriores.

#### Verificação curta pós-normalização Git `[FATO]`

| Check | Resultado |
|---|---|
| pytest V2 (arch+smoke+golden schema) | **11 passed, 1 xfailed** |
| `npm run check:api-drift` | Regenerado client → **up to date** |
| `npm run build` (v2/frontend) | **OK** |
| GET `/api/health` :8081 | **ok** (servidor já em execução) |

#### Consolidação documental (2026-07-22) `[FATO]`

| Item | Resultado |
|---|---|
| Canônicos V2 | `ROADMAP_V2_EPIC.md` · `docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md` · `docs/README.md` |
| Blueprint status | **Aprovado** — canônico atual **v0.2.3** (linha base v0.2; sconto/ownership em 0.2.2; ACCONTO vs Payment em 0.2.3) |
| V1 histórico | `docs/v1/` + `archive/` |

#### Checkpoint e baseline pré-move (2026-07-22)

| Item | Valor |
|---|---|
| Branch | `checkpoint/pre-foundation` |
| SHA | `7d7f39806a76972895ba60ec162d484eb410d175` |
| Import app | OK (`Epic Importações`) |
| Alembic | `014 (head)` |
| pytest | **30 failed / 294 passed / 2 skipped** (125s) |
| tsc | exit 2 (~28 erros; drift/imports) |
| vite build | OK (467 KB JS) |
| vitest | **1 failed / 47 passed** (`productColumnPrefs`) |
| health | OK |
| login/me | 200 (httpx) |
| backup-db.ps1 | OK → `backups/db/epic_importacao_20260722_142628.sql` |

#### Baseline pós-move V1 (mesmo checkpoint; CWD=`v1/`)

| Item | Valor | vs pré-move |
|---|---|---|
| Import | OK | match |
| Alembic | `014 (head)` | match |
| pytest | **30 failed / 294 passed / 2 skipped** | match (sem falha nova de path) |
| tsc / vite / vitest | mesmo padrão de falhas pré-existentes | match |
| health / login / me | 200 | match |
| backup-db.ps1 | OK → `v1/backups/db/` | path alinhado |

#### Scaffold V2 (2026-07-22)

| Item | Valor |
|---|---|
| Layout | `v2/app/{foundation,identity,audit,documents}` — **sem** stubs Orders/Billing/… |
| Bancos | `epic_v2` + `epic_v2_test` (Postgres `localhost:5433`) |
| Alembic V2 | `001` baseline |
| Porta | **8081** |
| pytest V2 | **11 passed, 1 xfailed** (arch + smoke + golden schema) |
| health/login/docs/audit | 200 (httpx smoke) |
| OpenAPI | `npm run generate:api` + `check:api-drift` OK |
| FE | login + shell autenticado; `vite build` OK |
| Goldens / harness | **DONE** — `parse_it_number` / `parse_it_date` via `v1/scripts/export_characterization_goldens.py --out-dir`; schema/presença verdes |
| Equivalência de cálculo V2↔golden | **Fora do DoD da Fundação** — tracked em §O Inc-6 (Order-to-Pay) |

**DoD:** implementação + teste automatizado + E2E + walkthrough + evidência neste doc + aceite operacional (quando couber) + roadmap atualizado.

### M.1 ADRs

| ADR | Decisão | Status |
|---|---|---|
| ADR-01 | Monólito modular; stack atual | Aceita |
| ADR-02 | Alt. B — portar calculadores com testes | Aceita |
| ADR-03 | Separar Order / Shipment / ImportProcess | Aceita |
| ADR-04 | Layout `root/{docs,ROADMAP,v1,v2}`; bancos e portas separados | Aceita |
| ADR-05 | OpenAPI + client TS gerado | Aceita |
| ADR-06 | Liquidação só via Payable | Aceita |
| ADR-07 | StockBalance derivado | Aceita |
| ADR-08 | `document_links` por Documents | Aceita |
| ADR-09 | Estados por agregado | Aceita |
| **ADR-10** | **Todo conteúdo atual descartável; V2 banco vazio; massa determinística; fixtures ≠ produção; comparação só comportamento/cálculos; zero migração de dados.** Reconfirmada pelo usuário em **2026-07-22**: registros com aparência operacional também pertencem à massa de teste; **inventários nominais / filtros `DEMO`/`QA`/`E2E` não alteram essa decisão** e não são gate de fase. Auditoria de inventário (só leitura, não bloqueante) pode ocorrer à parte, sem excluir dados e sem reclassificar ADR-10 por heurística de nomes. | **Aceita (definitiva)** |
| ADR-11 | Orders ← Billing ← Treasury; Expense em Costing | Aceita |
| ADR-12 | DUIMP→Invoice 1:N; Shipment sem order_id | Aceita |
| ADR-13 | `.env`/deps isolados; recriar venv V2; Cursor Rules revisadas | Aceita |
| **ADR-14** | **Modularidade interna e limites de complexidade** — package-by-domain; ownership; contratos públicos; internals privados; **grafo canônico acíclico** (Blueprint §5.16: `A-->B` = A depende da API pública de B); Identity/Audit/Documents **sem ciclos** (Audit/Documents com actor opaco; Identity orquestrado via Foundation); routers/páginas finos; gatilhos de revisão; testes AST de imports (**inclui falha V2→V1**); revisão manual de coesão/god files; exceções gerado/migrations/fixtures; **proibição absoluta** de import `v2/**`→`v1/**` inclusive testes; caracterização só via golden | **Aceita** |
| **ADR-15** | **Audit atômico** — ação crítica + `Audit.record_event` na **mesma** `UnitOfWork` / commit PostgreSQL; Foundation orquestra Identity/Documents + Audit; proibido commit da entidade + audit “best effort” depois | **Aceita** |
| **ADR-16** | **V1 congelada funcionalmente** desde **2026-07-22**. Não recebe features, redesign de UI, evolução de modelo ou execução de pendências históricas F0–F12. Alterações em `v1/**` só para: manter baseline executável; corrigir geração de goldens; risco crítico de segurança/perda de dados; paths/scripts indispensáveis à caracterização V1→golden. | **Aceita** |

### M.2 GATE-FONTES — resolvido e fechado ✅

- Sem servidor/banco de produção separado.
- **Todo** o workspace (banco, backups, anexos, planilhas, PDFs, usuários, DEMO/QA/E2E) = teste descartável.
- **Não** há repopulação operacional a partir de “fontes”.
- **Não** há conciliação de registros V1↔V2.
- Documentos atuais = candidatos a **fixture/golden file** apenas.

### M.3 Cenários canônicos

Índice operacional; especificação de aceite em **Blueprint §15** (SC-01…SC-17):

1. Ordem multi-invoice · 2. Scadenze → N Payables · 3. Allocations · 4. Antecipo não alocado · 5. Multi-embarque via ShipmentItem · 6. Embarque parcial · 7. DUIMP 1:N invoices · 8. Retificação · 9. Nacionalização parcial · 10. Entreposto · 11. Crédito cruzado · 12. Landed cost SKU · 13. Documento supersedido · 14. Fechamento/reabertura · (+ criação manual, Ordine, conciliação no Blueprint).

### M.4 Rastreabilidade Order-to-Pay

Inalterada em substância (POST /orders, /invoices, /payments, /fx, /payables; `GET /orders/{id}/summary` via **Reporting**; documents; audit). Matriz REQ: Blueprint §17.

### M.5 Bloqueios e decisões abertas

| ID | Status | Bloqueia | Notas |
|---|---|---|---|
| L-001 | Aberto | Fase Conciliação / fechamento com tolerâncias | Não inventar política definitiva |
| L-003 | Aberto | Credit/CC BR avançado | Isolar na fase Treasury |
| DEC-DUIMP-MULTI-SHIP | Aberto | Customs multi-embarque | — |
| DEC-ENDERECO | Aberto | Modelo de endereços | — |
| **DEC-SCONTO-ITEM** | **Fechada** | Inc-2 Billing | `discount_type` NONE\|UNIT_AMOUNT\|PERCENT em InvoiceItem; HALF_UP 2 casas; Payable=net |
| **DEC-ACCONTO-INVOICE** | **Pendente** | Tipagem Billing / ingestão Fattura | Alvo `PROFORMA\|ACCONTO\|FINAL`; código V2 ainda só PROFORMA\|FINAL; ver Blueprint §5.7 |

#### DEC-SCONTO-ITEM — fechada (2026-07-22, Inc-2)

**Decisão:** sconto de linha ∈ **InvoiceItem** com representação dual (Fattura `% Sc` + Heroes €/un). `discount_type` xor; DRAFT pode incompleto; emissão exige tipo definido; derivados bruto/desconto/líquido; residual scadenze % na última parcela; desconto global Treasury fora do Inc-2.

#### Destino de itens históricos V1 (congelamento ADR-16)

| Item | Destino |
|---|---|
| **P1-b / P1-c sconto DA SPEDIRE** | Encerrado como implementação/política V1 (preview + persistência dispatch + não-propagação). Regra de negócio transferida para **DEC-SCONTO-ITEM** na V2. (Código rotula a não-propagação como P1-c; o gap comercial de sconto no preview/custo é o mesmo tema.) |
| **Produtos slug-shell** | Dívida de massa V1 (`is_slug_shell` no match Heroes). **Não migrar** para V2. Catalog V2 começa limpo. |
| **Redesign da fila AP** | **Não** implementar na V1. Já no Blueprint **§8.9**; execução no **Inc-5** Order-to-Pay (fila AP + cockpit read model). |

### M.6 Changelog

- **2026-07-23 — Rev 0.5.6 / Inc-4 DONE:** migration `005_fx`; três visões + N:M `FxExecutionAllocation`; HttpFxQuoteProvider (Frankfurter→AwesomeAPI); FE strip+painéis; gates canônicos −40/−90/−130; E2E `inc4-fx`; sem Accconto/Inc-5; sem commit.
- **2026-07-22 — Rev 0.5.4 (sync ACCONTO):** Blueprint **v0.2.3**; refuta tipagem automática ACCONTO sem exemplar; distingue Invoice ACCONTO vs Payment antecipado; corrige frase “ANTECIPO ≠ tipo; Treasury”; apêndice evidências separado Fundação vs pós-Inc-3.
- **2026-07-22 — Rev 0.5.3 (sync docs pós-Inc-3):** TOC §O + M.0 WIP alinhados a Inc-3 DONE; Blueprint changelog 0.2.2 explicitou ownership Inc-3; causa divergência advisor=upload v0.2 antigo.
- **2026-07-22 — Rev 0.5.2 / Inc-3 DONE:** migration `004_treasury`; Payment+Allocation batch idempotente; `billing.public.apply_payable_allocations` + eligible; FE Pagamentos; gates O.3; sem FX/Inc-4; sem commit.
- **2026-07-22 — Rev 0.5.1 (docs):** painel executivo de progresso; sincronização de status (Inc-1/Inc-2 DONE; Inc-3 NOT_STARTED; Order-to-Pay IN_PROGRESS; Blueprint v0.2.2); §L aponta só Inc-3; §O retitulado.
- **2026-07-22 — Revisão arquitetural Inc-2:** blockers/qty → queries; commands mantido; xfail parse_it = O.6; credencial DEV anotada; sem mudança de schema.
- **2026-07-22 — Inc-2 Billing+Payables DONE:** migration 003; DEC-SCONTO-ITEM fechada (NONE|UNIT_AMOUNT|PERCENT); FINAL/PROFORMA; Payables na emissão; FE+Playwright; sem Treasury/Inc-3; sem commit.
- **2026-07-22 — Fechamento técnico Inc-1 `[histórico]`:** RTL `OrdersPages.test.tsx` (8 Vitest); RBAC/audit-rollback; Playwright walkthrough completo; gates O.1 todos DONE (exceto REVIEW LOC routes). *Naquele momento* Inc-2 ainda não iniciado — **superado** (Inc-2 = DONE).
- **2026-07-22 — Inc-1 Catalog+Orders DONE (working tree):** modules catalog/orders; migration 002; FE features; Vitest+Playwright; decisões técnicas em §O.1; sem `/summary`; sem sconto no Inc-1.
- **2026-07-22 — Etapa 0 pré-Inc-1 (docs) `[histórico]`:** `DEC-SCONTO-ITEM` no Blueprint §6.6/§9.3 (v0.2.1); ADR-16 congelamento funcional V1; nota ADR-10; destinos P1-b/c sconto, slug-shell, fila AP. **Sem código Inc-1** *naquele momento* — **superado**.
- **2026-07-22 — §O cockpit ownership (rev 0.3.2):** `GET /api/orders/{id}/summary` mantido; composição financeira movida para `reporting.public.order_cockpit` / `OrderCockpitQuery` (Foundation orquestra). Orders **não** agrega Billing/Treasury (grafo §5.16 / Blueprint §5.6–5.15). Blueprint **não** alterado naquela revisão.
- **2026-07-22 — Consolidação canônica + DOC_DELTA (rev 0.3) `[histórico]`:** precedência interna; cabeçalho; B.0–B.2; Fundação DONE; harness/goldens DONE; equivalência `parse_it` → §O Inc-6; Blueprint **v0.2** *confirmado à época* — **supersedido** (hoje **v0.2.3**).
- **2026-07-22 — Normalização Git + política + Roadmap pós-Fundação `[histórico]`:** branch `main`; WIP Fundação sem commit; checkpoint `7d7f398`; seções B/I/L/M. *Naquele momento* Order-to-Pay ainda não implementado — **superado** (Inc-1/Inc-2 DONE; fase IN_PROGRESS).
- **2026-07-22 — Consolidação documental final:** Blueprint V2 *Aprovado*; Fase 0B DONE/APPROVED; V1 em `docs/v1/` + archive.
- **2026-07-22 — Fundação técnica executada:** checkpoint `7d7f398`; move `v1/`/`docs/v1/`; scaffold `v2/`; gates Fundação **DONE**.
- **2026-07-22 — Contrato pré-Fundação / Blueprint / ADR-14 / premissa de dados / diagnóstico.**

---

<a id="n-fundacao"></a>
## N. Fundação técnica (executada 2026-07-22)

Status: **DONE no working tree** (código + gates abaixo). Commit **não** é gate. Order-to-Pay: **IN_PROGRESS** (Inc-1/2/3 **DONE**; Inc-4 **NOT_STARTED**) — ver §L / §O.

### N.1 Checkpoint — DONE

| Item | Valor |
|---|---|
| Branch | `checkpoint/pre-foundation` |
| SHA | `7d7f39806a76972895ba60ec162d484eb410d175` |

### N.2–N.5 Move + gate V1 — DONE

Docs V1 consolidados em `docs/v1/`; monólito em `v1/`; Cursor V1 `globs: v1/**,docs/v1/**`; `v1/.venv` recriado. Baseline pós-move = pré-move (30f/294p/2s; sem regressão de path). Health/login OK. Layout inicial da Fundação **executado** (não há pendência “não executado nesta tarefa”).

### N.6 Scaffold V2 — DONE

```text
v2/app/foundation/   # create_app, settings, db, UoW, deps, auth/document/audit routes, health
v2/app/identity/     # models, security, public, seed (sem import Audit/Documents/Foundation)
v2/app/audit/        # models, public.record_event
v2/app/documents/    # models, public store/link (attachments_path injetado)
v2/frontend/src/features/auth + app-shell + api/generated/
v2/tests/architecture/test_import_boundaries.py
v2/tests/characterization/goldens/*.json
v2/tests/characterization/test_golden_schema.py
```

**Decisões de scaffold:** package-by-domain proporcional (sem camadas vazias); HTTP de Auth/Documents/Audit orquestrado na Foundation (Identity/Documents não importam Audit); `openapi-typescript` + `openapi-fetch`; porta 8081; bancos isolados.

**Grafo ALLOWED_DEPS agora:** identity→∅, audit→∅, documents→∅. Exceção ORM: `models.py` pode importar `app.foundation.database.Base`.

### N.7 Order-to-Pay

**Critério de saída da Fundação atendido.** Order-to-Pay (J#2) = **IN_PROGRESS**: Inc-1/2/3 **DONE**; próxima ação = **Inc-4** (§L / §O).

### N.8 Gate de modularidade — DONE

| Critério | Status | Evidência |
|---|---|---|
| Estrutura modular mínima | DONE | Pacotes sob `v2/app/*` |
| Grafo Blueprint §5.16 | DONE | `module_graph.py` + arch test |
| Cursor rules | DONE | router + V1 escopada + V2 architecture |
| Arch test | DONE | pytest arch verde |
| Sem ciclos; sem V2→V1 | DONE | arch test |
| BE/FE por domínio/feature | DONE | features/auth, app-shell; sem `api.ts` monolítico |
| Sem dump global multi-módulo | DONE | inspeção |
| Relatório §3.3 | DONE | N.9 abaixo |
| Exceções | DONE | gerado OpenAPI; alembic; Base ORM |

### N.9 Relatório manual gatilhos §3.3 / god files `[FATO]`

**V2 (Fundação):** nenhum arquivo manual ≥400 LOC. Maior: `test_import_boundaries.py` (~114), `identity/public.py` (~101). Routers Foundation sem regra de negócio de Orders/Billing. FE: LoginPage ~57, AppShell ~33.

**Exceções justificadas V2:** `frontend/src/api/generated/*` (gerado); `alembic/versions/001_baseline.py` (migration).

**V1 (legado, pós-move — dívida conhecida, não bloqueia Fundação):** god files acima do gatilho 600+ — `frontend/src/api.ts` (~1448), `services/order_central.py` (~1083), `FinancePanels.tsx` (~828), `models.py` (~644), etc. Não portar como monolitos; Order-to-Pay deve nascer modular.

### N.10 Matriz de gates Fundação

| Gate | Status |
|---|---|
| V1 executável pós-move; sem regressão path | DONE |
| V2 8081; `epic_v2` / `epic_v2_test` | DONE |
| Login/RBAC; Documents; Audit mesma UoW | DONE |
| OpenAPI + client + drift check | DONE |
| `test_import_boundaries` | DONE |
| Cursor Rules escopadas | DONE |
| Relatório §3.3 | DONE |
| ROADMAP evidências | DONE |
| Harness + goldens de caracterização (export + schema/presença) | DONE |
| Equivalência de cálculo V2 vs golden (`parse_it`) | **Não é gate da Fundação** — DoD de **Order-to-Pay** (§O Inc-6); placeholder `xfail` permanece até o porte |

**Nenhum gate da Fundação BLOCKED ou PARTIAL.** Fundação = **DONE no working tree**.

---

<a id="o-order-to-pay-plan"></a>
## O. Execução Order-to-Pay — Inc-1…Inc-3 concluídos

```text
Inc-1 = DONE
Inc-2 = DONE
Inc-3 = DONE
Inc-4–Inc-6 = TODO
```

Fase J#2 = **IN_PROGRESS**. Planos e evidências de Inc-1…Inc-4 abaixo são **histórico de execução concluída**, não trabalho pendente. Próxima ação: **Inc-5** (§L / §O.5).

**Estado Git a registrar `[FATO]`** (não alterar o repositório):

| Item | Valor |
|---|---|
| Branch **ativa** | `main` |
| Tip de `main` / HEAD | `008fb49` (= `origin/main`) — **não** confundir com o checkpoint |
| Checkpoint preservado | `checkpoint/pre-foundation` @ `7d7f398` (referência de segurança; **não** é HEAD) |
| Working tree | Fundação + Inc-1 + Inc-2 + Inc-3 + reorganização + docs = **WIP não commitado** sobre `main` |
| Política | Sem commits/branches/tags/stashes automáticos (router global) |
| Procedimento que alinhou `main` | `git symbolic-ref HEAD refs/heads/main` + `git reset` (índice); working tree intacto |

```text
git diff --stat main
# = conteúdo do commit checkpoint (vs main) + Fundação + mudanças posteriores no working tree

git diff --stat checkpoint/pre-foundation
# = Fundação + mudanças posteriores apenas

git status --short
# WIP completo não commitado; branch = main
```

**Baseline de partida V2 `[histórico — início Order-to-Pay, pós-Fundação]`:** na saída da Fundação havia só `foundation` / `identity` / `audit` / `documents`; FE auth+shell; goldens `parse_it_*` (schema OK; equivalência = O.6); porta 8081; **ainda sem** Catalog/Orders/Billing/Treasury. **Estado atual:** Catalog + Orders (**Inc-1 DONE**) + Billing + Payables (**Inc-2 DONE**) + Treasury (**Inc-3 DONE**). Ver §B.0.

#### DEC-CLOSE-ORDER `[DECISÃO]` (provisória)

- Inc-1 (O.1) implementou estados/ações **DRAFT**, **CONFIRMED** e **CANCELLED**.
- `CLOSED` pode existir no vocabulário/modelo, mas a **ação de fechamento fica adiada** até Billing existir e fornecer dados para validar a regra (ex.: ausência de Payable OPEN). *Billing já existe (Inc-2 DONE); fechamento CLOSED permanece fora do escopo até decisão explícita.*
- **Não** inventar fechamento só com dados de Orders.

#### DEC-FX-SCOPE `[DECISÃO]` (provisória)

- Order-to-Pay implementa taxa **prevista** e **realizada** vinculada ao pagamento/alocação (`ExchangeRate` mínimo).
- Contratos de hedge, bancos, spreads avançados e múltiplas pernas: **fora** deste slice.

**L-005 / L-006:** não bloqueiam O.1 — papéis baseline (Identity) + Catalog mínimo com campos avançados **nullable**.

**Fora do slice J#2:** SC-08 retificação; Credit/Discount/BrazilCurrentAccount (L-003); landed cost; Logistics/Customs; cadastro mestre Catalog completo.

**Grafo a estender em `module_graph.py` (alinhado ao Blueprint §5.16):**  
`catalog → {documents, audit}` · `orders → {catalog, documents, audit}` · `billing → {orders, catalog, documents, audit}` · `treasury → {billing, documents, audit}` · `reporting → {orders, billing, treasury}` (somente leitura de APIs públicas; **sem** escrita em domínio).

**Proibido no slice:** aresta `orders → billing` ou `orders → treasury` (viola grafo; Orders §5.6). Cockpit financeiro composto = **Reporting** (ou orquestração Foundation → Reporting), não `orders.public`.

### O.1 Inc-1 — Catalog mínimo + Orders

| Campo | Conteúdo |
|---|---|
| **Status** | **DONE** (working tree; sem commit) — fechamento técnico 2026-07-22 |
| **Objetivo** | Supplier/Product mínimos; Order+OrderItem; DRAFT→CONFIRMED/CANCELLED |
| **Entidades** | `Supplier`, `Product`; `Order`, `OrderItem` |
| **Invariantes** | SKU **unique global** (inclui inativos); edição só DRAFT; sem status fin/log/aduana; CLOSED sem comando (DEC-CLOSE-ORDER); `code` de negócio **informado** (não `ORD-seq`); optimistic lock `version` |
| **Migration** | `002_catalog_orders` |
| **Contratos públicos** | `catalog.public` / `orders.public` (fachadas finas → commands/queries) |
| **Endpoints** | suppliers/products CRUD mínimo; orders CRUD DRAFT; confirm/cancel; **`GET /orders/{id}` = detalhe comercial** — **sem** `/summary` (Inc-5) |
| **UI** | Fila; nova ordem; detalhe; Vitest+RTL + Playwright |
| **Testes** | unit; integração; arch; RBAC; Vitest; Playwright; walkthrough |
| **Evidências** | ver matriz de gates abaixo (pytest 27p/1xfail; Vitest 8p incl. RTL; Playwright 2p; alembic 002; browser MCP login→fila) |

#### Decisões técnicas Inc-1 `[DECISÃO]` (plano revisado 2026-07-22)

| Tema | Decisão |
|---|---|
| Numeração | `id` técnico; `code` negócio obrigatório (manual/futuro Ordine); `external_ref` nullable; `source_system` default `MANUAL`; sem geração `ORD-{YYYY}-{seq}`; sem `MAX+1` |
| Ator | `created_by_actor_id: str` (como Audit); obrigatório na criação manual; sem FK Identity |
| Decimal | qty/preço `Numeric(18,4)`; OpenAPI como **string**; sem persistir `line_total`; `commercial_total=null` se `unpriced_item_count>0` + `priced_subtotal` |
| HTTP | `routes.py` no módulo; Foundation só `include_router`; sem `api.py` stub; arch: `routes.py` pode importar foundation+audit |
| SKU | `UNIQUE(sku)` global |
| Seeds | roles/perms idempotentes; **sem** usuário `comprador@…` em `epic_v2` (só role) |
| Audit material | create, confirm, cancel, change supplier, add/remove item, change qty/price |
| Sconto | **fora do Inc-1** — resolvido em **DEC-SCONTO-ITEM** (**fechada**, Inc-2) |
| Status | **DONE** no working tree |

#### Endpoints Inc-1 (implementados)

`POST/GET /api/suppliers`, `GET /api/suppliers/{id}` · `POST/GET /api/products`, `GET /api/products/{id}` · `POST/GET /api/orders`, `GET/PATCH /api/orders/{id}` · `POST/PATCH/DELETE .../items` · `POST .../confirm` · `POST .../cancel` · **sem** `/summary` · **sem** `/close`

#### UI Inc-1

`features/orders` (fila, nova, detalhe) + `features/catalog` (API helpers); shell com nav; client OpenAPI gerado.

#### Gates Inc-1 (fechamento 2026-07-22)

| Gate | Status | Evidência |
|---|---|---|
| Catalog + Orders funcionais | DONE | módulos + API |
| Migration 002 `epic_v2` / `epic_v2_test` | DONE | `alembic current` → `002 (head)` ambos |
| Downgrade só DB descartável | DONE | downgrade **não** executado em `epic_v2` operacional nesta tarefa |
| API + FE | DONE | build + Playwright |
| OpenAPI drift | DONE | `check:api-drift` up to date |
| Arch (sem V2→V1; sem Orders→Billing) | DONE | `test_import_boundaries` |
| pytest V2 completo | DONE | **27 passed, 1 xfailed** |
| Catalog/Orders/RBAC/lock/totais/audit rollback | DONE | `test_catalog_*`, `test_orders_*`, `test_orders_rbac_audit` |
| Vitest + **RTL** | DONE | **8 passed** (`orderTotals` + `OrdersPages` RTL) |
| Playwright Inc-1 | DONE | `inc1-orders` + `inc1-walkthrough` **2 passed** |
| Walkthrough browser | DONE | Playwright walkthrough + MCP login→`/orders` |
| Audit mesma UoW + rollback | DONE | teste `test_audit_rollback_prevents_order_persist` |
| Sem Billing/Treasury / sem `/summary` | DONE | inspeção |
| Gatilho §3.3 | REVIEW | `orders/routes.py` ~407 LOC (HTTP thin; domínio em commands/queries) — justificado, sem god-file de domínio |

#### `DEC-SCONTO-ITEM` — fechada no Inc-2

Decisão e evidências: §M.5 / §O.2. **Não está aberta.** Pacote de decisão pré-Inc-2 foi **consumido**; Inc-2 = **DONE**.

### O.2 Inc-2 — Billing + Payables

| Campo | Conteúdo |
|---|---|
| **Status** | **DONE** (2026-07-22) |
| **Objetivo** | Invoice + items + PaymentTerms → N Payables; saldo Invoice derivado |
| **Entidades** | `Invoice`, `InvoiceItem`, `PaymentTerms`, `Payable` |
| **Invariantes** | Order 1:N Invoice; Invoice 1:N Terms → 1:N Payable; saldo Invoice = Σ Payable; nunca liquidar Invoice direto; ISSUED imutável (sem cancel ISSUED); `order_item_id` obrigatório |
| **DEC-SCONTO-ITEM** | Fechada: `NONE\|UNIT_AMOUNT\|PERCENT`; emissão exige tipo definido; HALF_UP 2 casas |
| **Tipos Invoice (Inc-2 entregue)** | `FINAL` \| `PROFORMA` no código/migration `003` |
| **ACCONTO / Payment antecipado** | `ACCONTO` **pode** ser tipo documental de Invoice em Billing (**DEC-ACCONTO-INVOICE** pendente — sem exemplar *Fattura di acconto* tipado nos PDFs disponíveis). **Pagamento antecipado** = Payment em Treasury. Invoice e Payment são entidades distintas; emitir Invoice **não** cria Payment. Operação admite Payment antecipado sem Invoice ACCONTO (SC-04). Lacuna código: V2 ainda sem `invoice_type=ACCONTO` |
| **Migration** | `003_billing` — aplicada `epic_v2` + `epic_v2_test`; heads=`003` à época; hoje stack em **004** pós-Inc-3 |
| **Contratos públicos** | `billing.public` (create/update/items/terms/issue/cancel_draft/list/balances) |
| **Endpoints** | `POST/GET /api/orders/{id}/invoices`; `GET/PATCH /api/invoices/{id}`; items/terms/issue/cancel; `GET /api/payables`; `GET .../invoiced-quantities` |
| **UI** | Painel na Order; formulário Invoice; listas Invoices/Payables |
| **Testes** | SC-01/02; matriz descontos/terms/qty/RBAC/audit; arch; Vitest/RTL; Playwright `inc2-billing.spec.ts` |
| **Gate** | ≥2 scadenze → ≥2 Payables OPEN; pytest+arch+FE+E2E verdes |
| **Arquivos** | `v2/app/billing/**`; FE `features/billing/**` |
| **REVIEW LOC** | `billing/routes.py` — HTTP/schemas/composição (domínio de blockers/qty movido a `queries`); `commands.py` mantido coeso (agregado Invoice write-side). Justificativa §O.2 revisão arquitetural |

#### Gates O.2

| Gate | Status | Evidência |
|---|---|---|
| Migration 003 | DONE | `alembic upgrade` epic_v2 + epic_v2_test; current/heads=003 |
| Domínio + API | DONE | `test_billing_api.py` |
| Documents + Audit | DONE | doc obrigatório / override; `test_billing_rbac_audit` rollback |
| UI mínima | DONE | Order panel + InvoiceDetail + listas |
| pytest | DONE | 44 passed + 1 xfailed (suite V2) |
| arch | DONE | billing no grafo; orders↛billing; billing↛treasury |
| typecheck/build | DONE | `npm run build` |
| Vitest/RTL | DONE | invoiceMath + BillingPages |
| OpenAPI drift | DONE | `check:api-drift` OK |
| Playwright | DONE | `inc2-billing.spec.ts` passed |
| Walkthrough | DONE | browser: nav Faturas/Payables + E2E fluxo completo |
| Sem Inc-3 | DONE | sem Payment/Allocation/FX |
| Sem commit/branch/stash | DONE | WIP preservado |

#### Cenário manual opcional (demo/teste — não operacional)

```text
URL: http://127.0.0.1:8081
Credencial DEV (somente desenvolvimento local / demo):
  admin@epic.com.br / admin123
  → seed via SEED_ADMIN_* em .env; NÃO é senha operacional.
  → Trocar SEED_ADMIN_PASSWORD antes de uso real em LAN.
  → Não usar esta credencial em massa/produção; ambiente de teste isolado.
Order: criar CONFIRMED 10 × €100 → Criar fatura
Desconto 10% → líquido €900
Scadenze 30%/70% → Payables €270 + €630
Anexar PDF → Emitir → readonly
Reinício: nova Order com código único (não reusa massa operacional)
```

#### Revisão arquitetural pós-Inc-2 (2026-07-22)

| Item | Decisão |
|---|---|
| `routes.py` | Removidas regras de blockers e cálculo de qty disponível → `queries`/`public` |
| `commands.py` | **Manter** — um agregado Invoice (draft→issue→cancel DRAFT); cálculos em `money.py` |
| xfail | `test_v2_parse_equivalence_placeholder` — **fora** DoD Inc-2; tracked §O.6 / Fundação |
| Credencial roadmap | Marcada explicitamente como DEV-only |
| Tipos / ACCONTO | Correção documental 0.5.4: não reabrir Inc-2; tipagem `ACCONTO` = futuro (DEC pendente); código permanece FINAL\|PROFORMA |

### O.3 Inc-3 — Payment + PaymentAllocation

| Campo | Conteúdo |
|---|---|
| **Status** | **DONE** (working tree; sem commit) — fechamento técnico 2026-07-22 |
| **Objetivo** | Payment; unallocated; alocação parcial/múltipla só em Payable |
| **Entidades** | `Payment`, `PaymentAllocation`, `PaymentAllocationBatch`; `Payable.version` + status `PARTIALLY_PAID`/`PAID` |
| **Invariantes** | Allocation → **somente** Payable; `amount_unallocated`; unallocated **não** reduz saldo; saldo Payable só via `billing.public.apply_payable_allocations`; batch all-or-nothing; idempotência lote (mesma chave+payload → replay; payload diferente → 409) |
| **Migration** | `004_treasury` — `epic_v2` + `epic_v2_test` em **004 (head)**; downgrade↔upgrade OK em DB descartável `epic_v2_migtmp` |
| **Contratos públicos** | `treasury.public` (register/allocate/cancel/list); `billing.public.apply_payable_allocations` + `list_eligible_payables` |
| **Endpoints** | `POST /api/payments` (+ `/with-document`); `GET /api/payments`; `GET /api/payments/{id}`; `GET …/eligible-payables`; `POST …/allocations`; `POST …/cancel` |
| **UI** | Nav Pagamentos; lista/registro/detalhe+alocação (`features/treasury/**`) |
| **Testes** | SC-03/04; idempotência/conflito; timeout-retry; concorrência Payments; elegíveis excluem PAID/CANCELLED; orphan doc cleanup; Audit rollback; arch |
| **Gate** | Unallocated → saldo igual; allocate 400+300 → residual 300; over-alloc bloqueado |
| **Evidências** | matriz abaixo + cenário manual |
| **Arquivos** | `v2/app/treasury/**`; `billing/liquidation.py`; FE `features/treasury/**`; `e2e/inc3-treasury.spec.ts` |

#### Decisões técnicas Inc-3 `[DECISÃO]`

| Tema | Decisão |
|---|---|
| Ownership saldo | Billing possui `Payable.balance`/status; Treasury **nunca** escreve `payables` |
| Elegíveis | Query pública Billing; HTTP `GET /api/payments/{id}/eligible-payables` deriva supplier/currency do Payment |
| Idempotência | Nível **lote** (`payment_allocation_batches.idempotency_key` + `payload_hash`) |
| Documento | Multipart `/payments/with-document`: paths rastreados; falha Audit/domínio → `_cleanup_files` (sem órfão silencioso) |
| Fora do Inc-3 | FX, Credit, Discount, Reporting, Inc-4 |

#### Matriz de gates Inc-3 `[FATO]`

| Gate | Status | Evidência |
|---|---|---|
| pytest (suite V2) | DONE | **56 passed, 1 xfailed** |
| arch `test_import_boundaries` | DONE | treasury→billing.public; billing↛treasury |
| alembic current/heads | DONE | `epic_v2` + `epic_v2_test` = **004 (head)** |
| alembic down/up | DONE | DB descartável: `004→003→004` |
| typecheck + build | DONE | `tsc --noEmit` + `vite build` |
| Vitest/RTL | DONE | **15 passed** (incl. treasury list RTL) |
| OpenAPI drift | DONE | `check:api-drift` OK pós `generate:api` |
| Playwright | DONE | `e2e/inc3-treasury.spec.ts` **1 passed** |
| Walkthrough browser | DONE | Payment #4: €400+#11 + €300+#12 → Residual **300.00** |
| Sem FX/Credit/Discount/Inc-4 | DONE | escopo respeitado |
| Sem commit/branch/stash | DONE | WIP preservado |

#### Cenário manual utilizável (DEV)

```text
URL: http://127.0.0.1:8081
Credencial DEV (somente desenvolvimento local / demo):
  admin@epic.com.br / admin123
  → seed SEED_ADMIN_*; NÃO é senha operacional; trocar antes de LAN.

Dados seedados 2026-07-22 (epic_v2) — recriáveis se apagados:
  Fornecedor: INC3 Manual Fornecedor 180845 (id 14)
  Order: INC3-ORD-180845 (id 14) · Invoice: INC3-F-180845 (id 6) · net €1300
  Payable A #11 €600 · Payable B #12 €700
  Payment #4 ref INC3-WALK-180845 · €1000 REGISTERED
  URL direta: http://127.0.0.1:8081/payments/4

Roteiro (≤10 passos) — valores esperados:
  1. Login com credencial DEV acima
  2. Nav → Pagamentos → abrir Payment #4 (ou ref INC3-WALK-180845)
  3. Confirmar Residual 1000.00 e 2 elegíveis (#11 saldo 600, #12 saldo 700)
     (se já alocado neste seed: Residual 300.00 — pular p/ passo recriar)
  4. Alocar 400 no Payable #11 → confirmar → Residual 600.00; #11 PARTIALLY_PAID saldo 200
  5. Alocar 300 no Payable #12 → Residual 300.00; #12 saldo 400; Invoice balance 600
  6. Tentar alocar 9999 → erro (excede residual)
  7. Nav → Payables: #11/#12 com saldos acima
  8. (Opcional) Registrar novo Payment €50 sem doc (override admin) → SC-03: saldos iguais até alocar
  9. (Opcional) Replay: mesma idempotency_key+payload via API → sem double-alloc
 10. Logout

Recriar o cenário do zero:
  - Nova Order CONFIRMED: 13 × €100 = €1300, mesmo fornecedor novo
  - Invoice FINAL + terms AMOUNT 600+700 + emitir (doc ou issue_without_document)
  - Pagamentos → Novo: mesmo supplier, €1000, comprovante PDF → Alocar 400 depois 300
  - Códigos únicos (timestamp) para não colidir
```

**Próxima ação após Inc-3:** **Inc-4 (O.4)** — FX mínimo — ainda em `main`, **sem** commit automático.

### O.4 Inc-4 — FX (três visões) = Inc-4A + Inc-4B

**Regra:** `Inc-4 DONE` ⇔ `Inc-4A DONE` ∧ `Inc-4B DONE`. Inc-5 **não** inicia após só 4A.

#### O.4a Inc-4A — domínio FX

| Campo | Conteúdo |
|---|---|
| **Status** | **DONE** |
| **Objetivo** | Três visões (projetada/online/realizada); valuations; Manual/Fixture provider |
| **Entidades** | FxPlanRate, FxMarketQuote, FxExecution, FxExecutionAllocation, FxAllocationValuation |
| **Migration** | `005_fx` (alembic head; down/up OK em `epic_v2`) |
| **Invariantes** | Billing↛Treasury; reforecast≠altera valuation; null≠0 online; benchmarks nomeados |
| **UI/API** | fx-plan, executions, links, quotes manual, fx-view; painéis Payable/Payment |
| **Testes** | `test_fx_money` (−40/−90/−130); `test_fx_api`; arch; Vitest `fxApi`; Playwright `inc4-fx.spec.ts` |
| **Evidências** | pytest 66p/1xfail; arch green; OpenAPI drift OK; E2E canônico −40/−90/−130; walkthrough UI strip + painéis |

#### O.4b Inc-4B — provider HTTP

| Campo | Conteúdo |
|---|---|
| **Status** | **DONE** |
| **Objetivo** | Frankfurter→AwesomeAPI atrás de FxQuoteProvider; refresh mount/click; stale |
| **Gate** | falha explícita; sem fallback plan/realized; `HttpFxQuoteProvider` só na borda (`fx_routes`) |
| **Evidências** | refresh no `FxQuoteStrip` (mount+click); teste provider fallback AwesomeAPI; stale ainda calcula |

**Inc-4 DONE** = 4A ∧ 4B (2026-07-23). **Próxima ação:** Inc-5 (§O.5) sob pedido explícito — sem commit automático.

### O.5 Inc-5 — Fila de contas a pagar + cockpit read model (Reporting)

| Campo | Conteúdo |
|---|---|
| **Status** | **TODO** |
| **Objetivo** | Fila AP (Billing); cockpit da ordem = **read model transversal** que compõe leituras públicas — **não** vive em Orders |
| **Entidades** | Nenhuma nova de escrita; projeção de leitura (`OrderCockpitView` / DTO) |
| **Invariantes** | Cockpit **não** escreve domínio; sem `order_central`; **Orders não importa Billing/Treasury**; Reporting (ou Foundation→Reporting) só chama **APIs públicas de leitura**; sem internals |
| **Migration** | Nenhuma (ou view SQL opcional depois, ainda read-only) |
| **Contratos públicos** | `billing.public.payables_queue`; leituras `orders.public` (comercial), `billing.public` (invoice/payable balances), `treasury.public` (allocated/unallocated); **`reporting.public.order_cockpit`** (`OrderCockpitQuery`) = composição do resumo |
| **Ownership do HTTP** | `GET /api/orders/{id}/summary` permanece como rota funcional (UX/OpenAPI), mas o **handler** orquestra via Foundation → `reporting.public.order_cockpit` — **não** via `orders.public` agregando financeiro |
| **Endpoints** | `GET /api/orders/{id}/summary` (Reporting por baixo); `GET /api/payables` (fila Billing) |
| **UI** | Cockpit mínimo (cards + drill-down) em feature FE que consome o summary; fila financeira |
| **Testes** | summary read-only (sem side effects); arch: `orders` ↛ `billing`/`treasury`; `reporting` → só `public` de Orders/Billing/Treasury; Reporting sem comandos de escrita de domínio |
| **Gate** | Summary composto sem escrita; fila lista obrigações; **arch prova ausência de Orders→Billing/Treasury** |
| **Evidências** | E2E parcial + arch pytest + Roadmap |
| **Arquivos previstos** | `v2/app/reporting/public.py` (`order_cockpit` / `OrderCockpitQuery`); opcional `reporting/queries/`; rota em `foundation` (ex. `orders_read_routes` ou router de summary); `module_graph.py` + `ALLOWED_DEPS["reporting"]`; FE cockpit; **não** colocar composição financeira em `orders/public.py` |

### O.6 Inc-6 — E2E, walkthrough, goldens e aceite

| Campo | Conteúdo |
|---|---|
| **Status** | **TODO** |
| **Objetivo** | Fluxo vertical completo; OpenAPI drift; goldens finance + equivalência `parse_it` |
| **Entidades** | — |
| **Invariantes** | V2↛V1; equivalência só quando implementação V2 passar vs golden; cockpit E2E via `GET .../summary` **sem** regressão de grafo |
| **Migration** | — |
| **Contratos / endpoints / UI** | Fluxo ponta a ponta já exposto nos Inc anteriores (summary = Reporting) |
| **Testes** | Playwright E2E; browser walkthrough; `check:api-drift`; export goldens V1 `--out-dir`; xfail→pass; arch regression Orders↛Billing/Treasury |
| **Gate** | DoD J#2: SC-01…04 + E2E + arch + drift + evidência Roadmap |
| **Evidências** | comandos + prints no Roadmap |
| **Arquivos previstos** | `v2/frontend/e2e/**`; `v1/scripts/export_characterization_goldens.py` (cenários finance); goldens em `v2/tests/characterization/goldens/` |

**Fatia de aceite:**

```text
Supplier + Product → Order + items → CONFIRM → Invoice → N Payables
→ Payment unallocated (saldo inalterado) → allocate parcial (residual)
→ FX → Document → fila AP → GET /api/orders/{id}/summary (Reporting/OrderCockpitQuery)
→ Audit (mesma UoW nas ações críticas)
```

**Próxima ação após este plano:** executar **Inc-4 (O.4)** sob pedido explícito — ainda em `main`, **sem** commit automático.

---

<a id="apendice-evidencias"></a>
## Apêndice — Evidências

### Baseline histórico da Fundação `[histórico]`

- Checkpoint `7d7f398` em `checkpoint/pre-foundation`; baselines pré/pós-move em §M.0; Fundação em §N.
- `ROOT_DIR` V1 alinhado a `v1/`; scripts PowerShell sob `v1/scripts/`.
- Scaffold V2 **inicialmente** sem Catalog, Orders, Billing ou Treasury.
- pytest Fundação (revalidado à época): **11 passed, 1 xfailed**; smoke 8081 health/login/documents/audit; OpenAPI drift check OK.
- Premissa de dados e layout: decisão do usuário 2026-07-22.
- Extratos temporários `_tmp_pdfs/`: só leitura histórica; não são fixture canônica.
- Sem `app/`/`frontend/` na raiz; monólito em `v1/`.

### Estado atual pós-Inc-3 `[FATO]`

- Módulos: Catalog, Orders, Billing e Treasury **implementados** (working tree).
- pytest V2: **56 passed, 1 xfailed** (fechamento Inc-3).
- Alembic: **004 (head)** em `epic_v2` / `epic_v2_test`.
- Inc-1…Inc-4 = **DONE**; Inc-5 = **TODO**.
- Blueprint canônico **v0.2.3**; Roadmap **v0.5.4**.

**Limitações abertas (não contradizem Fundação/Inc-1/Inc-2/Inc-3 DONE):** L-001/L-003; **DEC-ACCONTO-INVOICE**; DEC-DUIMP-MULTI-SHIP; DEC-ENDERECO; equivalência `parse_it` V2↔golden pendente em **§O Inc-6** (`test_v2_parse_equivalence_placeholder` xfail).

**Documentação:** Blueprint V2 **v0.2.3**; `docs/README.md` (DOC_DELTA); `docs/v1/*`; ADR-14/15/16; regra Cursor V1 congelada.
