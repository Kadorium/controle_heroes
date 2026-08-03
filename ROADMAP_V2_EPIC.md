# EPIC Controle V2 — Roadmap operacional

> Fonte operacional: estado, sequência, gates, ADRs, bloqueios e próximos passos.
> Destino de produto: [`docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md`](docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md).
> Índice: [`docs/README.md`](docs/README.md).
> Histórico até Inc-6: [`docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md`](docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md) (**imutável**).
> Runtime/layout/start: [`README.md`](README.md) · método: [`.cursor/rules/epic-v2.mdc`](.cursor/rules/epic-v2.mdc).

| Campo | Valor |
|---|---|
| Versão | **0.5.62** — J#5 **DONE** (I5-0…I5-6); SC-07/09/10 aceitos |
| Atualização | **2026-08-03** |
| Última entrega | **I5-6** — E2E aceite J#5 + screenshots 1366; UI **ACCEPTED_WITH_MINOR_BACKLOG** |
| Próxima ação | **Planejar J#3** (Ingestão) — **não iniciar execução sem plano** |

**Nota:** a numeração J#3/J#4/J#5 é identificador histórico de rastreabilidade (REQ/ADR). A **ordem de execução** vigente é J#4 → J#5 → J#3 → J#6….

---

## 1. Estado atual

**Fonte única de status.**

| Item | Valor |
|---|---|
| Fundação | **DONE** |
| Order-to-Pay (J#2) / Inc-1…Inc-6 | **DONE** |
| Logística (J#4) | **DONE** |
| Patch J4-UX1 (modal + prestador) | **DONE** |
| Patch J4-UX2 (Document Readiness A1 Logistics) | **DONE** |
| Document Readiness A2 (Orders/Billing) | **DONE** |
| DR-UX (fechamento operacional/visual UI) | **DONE** — aceite Logistics **ACCEPTED_WITH_MINOR_BACKLOG**; patch H-FIX 0.5.54 |
| Document Readiness (campanha capacidade) | **DONE** |
| Aduana + Inventory (J#5) | **DONE** — I5-0…I5-6; SC-07/09/10 aceitos (evidência [`etapa-j5/`](docs/v2/etapa-j5/)) |
| Ingestão (J#3) | **TODO** — após J#5 (reposicionada); próxima = **planejar** |
| Etapa 9 / 9V (Horizon A) | **DONE** |
| Visual Horizon A | **ACCEPTED_WITH_MINOR_BACKLOG** |
| Horizon B1 (artefato externo) | **NOT_STARTED** — não incorporar sem decisão humana |
| Baseline J#4 | **2026-07-31** — evidências em [`docs/v2/etapa-j4/`](docs/v2/etapa-j4/) |
| Evidência J#5 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| Alembic head | `015_nationalization_inventory` |
| Foothold ingestão | `v2/app/ingestion/parse_it` (goldens) — **sem** pipeline J#3 |
| Docs intermediários | Status em `etapa-*` pode ser histórico; **canônico** = este Roadmap |

### Próxima ação autorizada (única)

**Planejar J#3** (Ingestão) sob pedido explícito — **não iniciar execução** nesta versão.

- J#5 fechado: ImportProcess 1:N; Doganale; Numerário→Payable; nacionalização; estoque derivado; UX SCR-019/022/024/025; E2E `e2e:j5` + aceite UI.
- SC-07 / SC-09 / SC-10: aceitos com evidência em [`UI_ACCEPTANCE_J5.md`](docs/v2/etapa-j5/UI_ACCEPTANCE_J5.md) / [`J5_EXECUTION_REPORT.md`](docs/v2/etapa-j5/J5_EXECUTION_REPORT.md).
- Sem Costing/J#6. Sem pipeline J#3.
---

## 2. Mapa do programa

Ordem de execução (IDs preservados): **J#4 → J#5 → J#3 → J#6 → J#7 → J#8**.

| Fase | Objetivo | Status | Gate de saída | Evidência | Próxima ação |
|---|---|---|---|---|---|
| 0B — Contrato | Roadmap + Blueprint aprovados | **DONE** | APPROVED 2026-07-22 | snapshot 0.5.42 | — |
| Fundação | Layout `v1/`+`v2/`; Identity/Audit/Documents; harness | **DONE** | Gates Fundação | snapshot §N | — |
| Order-to-Pay (J#2) | Orders + Billing + Treasury; equivalência `parse_it` | **DONE** | DoD J#2 (Inc-1…Inc-6) | [`docs/v2/etapa-inc-6/`](docs/v2/etapa-inc-6/) | — |
| Logística (J#4) | Shipment + packages/refs/summaries; operação manual | **DONE** | DoD §§5.10, 7.7–7.8 + Planning | [`docs/v2/etapa-j4/`](docs/v2/etapa-j4/) | — |
| Aduana + Inventory (J#5) | ImportProcess 1:N; estoque; Numerário | **DONE** | DoD + fixture Numerário + I5-0…I5-6; SC-07/09/10 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) | — |
| Ingestão (J#3) | Pipeline + adapters + commit via APIs públicas | **TODO** | Golden files + commit operacional idempotente do pipeline (não Git) | — | **Planejar** |
| Costing / Reconciliation (J#6) | Landed cost + pares | **TODO** | Equivalência de cálculo vs V1 | — | Após Ingestão (ordem: J#3 → J#6) |
| Dashboard (J#7) | Read models | **TODO** | DoD | — | Após Costing |
| Aceite final (J#8) | SC-* + arquivar V1 | **TODO** | V2 aceita; V1 arquivada | — | Após Dashboard |
| UI Horizon A | Shell + 12 SCR + polish adaptativo | **DONE** | ACCEPTED_WITH_MINOR_BACKLOG | [`docs/v2/etapa-9/`](docs/v2/etapa-9/) · [`docs/v2/etapa-9v/`](docs/v2/etapa-9v/) | MINOR_BACKLOG sob pedido |

Detalhe histórico: snapshot 0.5.42. Inc-6 checkpoints I6-0…I6-4: todos PASS. Aceite SC-01…SC-17: Blueprint §15 (Order-to-Pay cobriu SC-01…04 no E2E Inc-6). SC-05/SC-06 exercitáveis via Logistics J#4. **SC-07/09/10 = aceitos em J#5** (I5-6).

---

## 3. Fase concluída — Logística J#4 (DONE)

**Status: DONE.** Evidências: [`docs/v2/etapa-j4/`](docs/v2/etapa-j4/).

| Campo | Conteúdo |
|---|---|
| Objetivo | Embarques manuais via API/UI (Blueprint §§5.10, 7.7–7.8, 8.15; ADR-12) |
| Entregue | Migration `007`; módulo `logistics`; FE `/shipments`; `e2e:logistics` |
| DECs | Consolidadas no Blueprint 0.2.12 (incl. DEC-SHIP-PROVIDER); **DEC-SHIP-CANCEL aberta** para BOOKED+ |
| L-001 | Tolerância provisória em `logistics/divergence.py` — política final na Reconciliation |
| Patch J4-UX1 | Modal controlado; `LogisticsProvider`; FK + snapshot; BOOKED exige modal+prestador; FE selects + `/logistics-providers` |
| Patch J4-UX2 | PackageContent snapshots; batch packages; DocumentSummary provenance; UI volumes/docs; evidência [`docs/v2/etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| Fora (J#4) | Ingestion; Customs; Inventory; Horizon B1; Packing List automático; seed de prestador real (nome não comprovado) |
| Document Readiness A2 | Orders/Billing dates/unit/notes/docs — **DONE** (mesmo pacote de evidência `etapa-doc-readiness`) |

---

## 3b. Fase concluída — Aduana + Inventory J#5 (DONE)

**Status: DONE.** Evidências: [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/). Blueprint **0.2.15**. Aceite UI: **ACCEPTED_WITH_MINOR_BACKLOG**.

| Campo | Conteúdo |
|---|---|
| Objetivo | ImportProcess/DUIMP; Doganale; Numerário; nacionalização; estoque derivado; SC-07/09/10 |
| Entregue | Migrations **011…015**; módulos `customs`/`inventory`; FE `/customs`, `/inventory/*`; papéis `aduana`/`estoque`; `e2e:j5` |
| Aceite | SC-07/09/10 — evidência [`UI_ACCEPTANCE_J5.md`](docs/v2/etapa-j5/UI_ACCEPTANCE_J5.md); relatório [`J5_EXECUTION_REPORT.md`](docs/v2/etapa-j5/J5_EXECUTION_REPORT.md) |
| Fora | J#3 staging/parser; J#6 landed cost; Payment allocation Customs (gap intencional) |

### Checkpoints

| ID | Escopo | Status | Gate |
|---|---|---|---|
| **I5-0** | Decisões Blueprint; scaffold `customs`/`inventory` + public stubs; module_graph; RBAC; docs etapa-j5 | **DONE** | arch + `test_j5_i5_0_scaffold` |
| **I5-1** | Migration **011**: ImportProcess + joins + alocações item + lifecycle DRAFT/SUBMITTED/CANCELLED + UI `/customs` | **DONE** | pytest + vitest + e2e:j5-i5-1 |
| **I5-2** | Migration **012**: Doganale versionada + divergências + UI | **DONE** | supersede / is_current; e2e:j5-i5-2 |
| **I5-3A** | Migration **013**: CustomsFundingRequest + Payee + bases/tax/expense + UI | **DONE** | empty≠0; structured×declared; confirm → I5-3B Payable |
| **I5-3B** | Migration **014** (Billing): Payable extension + FundingPayableLink + regressão Inc-6/AP | **DONE** | suite regressão PASS; gap alocação Payment documentado |
| **I5-4** | Migration **015**: Nationalization + Inventory + SkuPosition + UI | **DONE** | SC-09/SC-10; bonded pré-nac; oversubscription 409 |
| **I5-5** | UX transversal SCR-019/022/024/025 (+ papéis `aduana`/`estoque`) | **DONE** | Vitest + pytest roles + e2e smoke |
| **I5-6** | E2E + screenshots 1366 + aceite | **DONE** | e2e:j5 (4); SC-07/09/10; Roadmap J#5 DONE |

### DECs J#5

| ID | Estado |
|---|---|
| DEC-DUIMP-MULTI-SHIP | **Fechada** (I5-0) — process 1:N shipment + UNIQUE + ShipmentItem alloc |
| L-007 DI vs DUIMP | Aberta — DI = tipo documental opcional |

---

## 4. Fases posteriores

| Fase | Resumo | Blueprint | Pré-requisito |
|---|---|---|---|
| Ingestão (J#3) | Automação transversal: arquivo→hash→adapter→staging→revisão→`public(owner)`→commit_batch; Ordine/Fattura/Packing/Doganale/Numerário/XLSX/PrintDeclaration | §§5.9, 7.2, 10 | **Customs + Inventory (J#5) DONE** — **próxima a planejar** |
| Costing / Reconciliation (J#6) | Expense + landed cost; pares; L-001 | §§5.13–5.14, 7.12–7.16, 9 | Após J#3 (ordem programa) / Aduana DONE |
| Dashboard (J#7) | Read models; Reporting RO | §§5.15, 8.2, 12 | Costing |
| Aceite final (J#8) | SC-01…SC-17; arquivar V1 | §15 | Dashboard |

---

## 5. Decisões abertas e bloqueios

| ID | Estado | Fase afetada | Bloqueia J#5 agora? | Bloqueia J#3 (após J#5)? | Próxima decisão |
|---|---|---|---|---|---|
| L-001 | Aberto (provisória em J#4) | Conciliação / tolerâncias | Não (J#5 DONE) | Não | Política final na Reconciliation |
| DEC-SHIP-CANCEL | Aberto | Logistics BOOKED+ | Não | Não | Isolar ou resolver em incremento Logistics |
| L-003 | Aberto | Credit / CC BR avançado | Não | Não | Isolar na fase Treasury |
| L-005 | Aberto | RBAC `reporting:read` | Não | Não | Validar matriz de papéis |
| DEC-ACCONTO-INVOICE | Pendente | Billing / ingestão Fattura | Não | **Possível** | Tipagem `PROFORMA\|ACCONTO\|FINAL` — Blueprint §5.7 |
| DEC-DUIMP-MULTI-SHIP | **Fechada** (I5-0) | Customs multi-embarque | Não | Não | Ver Blueprint §6.6 |
| DEC-ENDERECO | Aberto | Modelo de endereços | Não | Não | — |
| DEC-CLOSE-ORDER | Provisória | Orders `CLOSED` | Não | Não | Até decisão explícita |
| DEC-SCONTO-ITEM | **Fechada** | Billing | Não | Não | `NONE\|UNIT_AMOUNT\|PERCENT`; HALF_UP 2 casas |
| DEC-FX-SCOPE | **Fechada** | Treasury FX | Não | Não | Três visões; snapshot §O.4 |
| L-007 | Aberto | DI vs DUIMP | Não | Não | Isolar; DI documental |

---

## 6. ADRs vigentes

Detalhe: snapshot 0.5.42 §M.1 · impacto normativo: Blueprint.

| ADR | Decisão resumida | Impacto atual |
|---|---|---|
| ADR-01 | Monólito modular; stack atual | Stack V2 |
| ADR-02 | Alt. B — portar calculadores com testes | Ingestão / Costing / FX |
| ADR-03 | Separar Order / Shipment / ImportProcess | Modelo J#4+ |
| ADR-04 | Layout `root/{docs,ROADMAP,v1,v2}`; bancos/portas separados | Layout vigente |
| ADR-05 | OpenAPI + client TS gerado | Drift check |
| ADR-06 | Liquidação só via Payable | Billing/Treasury |
| ADR-07 | StockBalance derivado | Inventory J#5 |
| ADR-08 | `document_links` por Documents | Documents sem ciclos |
| ADR-09 | Estados por agregado | Todos os módulos |
| ADR-10 | Conteúdo atual descartável; zero migração de dados | Premissa definitiva |
| ADR-11 | Orders ← Billing ← Treasury; Expense em Costing | Ownership |
| ADR-12 | DUIMP→Invoice 1:N; Shipment sem `order_id` | Customs/Logistics |
| ADR-13 | `.env`/deps isolados; regra Cursor; venv V2 | Runtime |
| ADR-14 | Package-by-domain; grafo acíclico; proibição V2→V1 | Arch gates |
| ADR-15 | Audit atômico — mesma UoW | Fundação+ |
| ADR-16 | V1 congelada (2026-07-22) | Guarda `v1/**` |

GATE-FONTES fechado (ADR-10).

---

## 7. Manutenção do Roadmap

Gates técnicos transversais (Git, bancos, arch, OpenAPI, Audit, evidências): [`.cursor/rules/epic-v2.mdc`](.cursor/rules/epic-v2.mdc). Atualizar este Roadmap **após** gates da entrega; status só com evidência.

| ID | Regra |
|---|---|
| **R1** | Fase concluída → status, gate, evidência e resumo curto aqui; detalhe em `docs/v2/etapa-*`. **Não** adicionar ao snapshot 0.5.42. |
| **R2** | Pendência de execução → §8 com ID. |
| **R3** | Estado corrente **somente** no §1. |
| **R4** | Se > ~600 linhas: condensar DONE; mover detalhe para evidências. **Não** alterar o snapshot. **Não** criar snapshot a cada entrega. |
| **R5** | Ao **iniciar** execução (após plano), decompor checkpoints na seção da fase **antes** de executar. |

Novo snapshot integral: só com decisão explícita excepcional.

---

## 8. Backlog fora da fase

| Item | Destino | Bloqueia J#5? | Observação |
|---|---|---|---|
| MINOR_BACKLOG UI (InvoiceDetail LOC; row-highlight; aceite SCR-008; virtualização) | UI sob pedido | Não (DONE) | Aceite Horizon A fechado |
| MINOR_BACKLOG J#5 (link `/ap`; users seed aduana/estoque; Payment Customs; in_transit) | UI / Identity / Treasury | Não | [`UI_ACCEPTANCE_J5.md`](docs/v2/etapa-j5/UI_ACCEPTANCE_J5.md) |
| SCR-028 hub FX | UI futuro | Não | TARGET; sem rota `/fx` |
| Horizon B1 (externo) | Artefato externo | Não | NOT_STARTED |
| Débitos FX (N:M; Σ BRL; weekend provider; LOC FxPanels) | Polish Treasury | Não | Aceitos no Inc-4 DONE |
| Capacidades Blueprint futuras | J#3+ | — | — |

---

## 9. Histórico recente

| Rev | Resumo | Evidência |
|---|---|---|
| **0.5.62** | J#5 **DONE** (I5-6 E2E + screenshots 1366 + aceite SC-07/09/10; UI ACCEPTED_WITH_MINOR_BACKLOG); Alembic head 015; próxima = planejar J#3 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.61** | J#5 I5-5 **DONE** (UX transversal SCR-019/022/024/025; papéis `aduana`/`estoque`; labels pt-BR; Audit/DocumentActions); J#5 permanece IN_PROGRESS; próxima = I5-6 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.60** | J#5 I5-4 **DONE** (migration 015 Nationalization+Inventory+SkuPosition; UI Liberações/Recebimentos; SCR-024/025 mínimo); J#5 permanece IN_PROGRESS; próxima = I5-5 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.59** | J#5 I5-3B **DONE** (migration 014 Payable Customs + FundingPayableLink; AP denormalizado; sem redesign Treasury); próxima = I5-4 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.58** | J#5 I5-3A **DONE** (migration 013 Payee+FundingRequest+linhas; UI Numerário; confirm sem Payable); próxima = I5-3B | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.56** | J#5 I5-1 **DONE** (migration 011 ImportProcess; joins; alocações; lifecycle; UI `/customs`; e2e:j5-i5-1); sequência 011…015 documentada; próxima = revisar I5-1 → I5-2 | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.55** | J#5 **IN_PROGRESS**; I5-0 **DONE** (Blueprint 0.2.15; DEC-DUIMP-MULTI-SHIP fechada; scaffolds customs/inventory; module_graph; RBAC; etapa-j5) | [`docs/v2/etapa-j5/`](docs/v2/etapa-j5/) |
| **0.5.54** | DR-UX patch corretivo H-FIX **DONE** (qty wire, Provenance, Invoice 1366, download/gates/screenshots); A1/A2 DONE; próxima = planejar J#5 | [`docs/v2/etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| **0.5.53** | DR-UX **DONE** (UI Documents download, supplier, Logistics contents/`source_line_reference`/summary); A1/A2 capacidade DONE; aceite Logistics ACCEPTED_WITH_MINOR_BACKLOG; próxima = planejar J#5 | [`docs/v2/etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| **0.5.52** | Document Readiness A2 **DONE**; Blueprint 0.2.14; Alembic 010; A1+J#4 DONE; Document Readiness concluído; próxima = planejar J#5 | [`docs/v2/etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| **0.5.51** | J4-UX2 Document Readiness A1 **DONE**; Blueprint 0.2.13; Alembic 009; J#4 DONE; próxima = A2 Orders/Billing depois J#5 | [`docs/v2/etapa-doc-readiness/`](docs/v2/etapa-doc-readiness/) |
| **0.5.50** | J4-UX1 **DONE** (modal + LogisticsProvider); Blueprint 0.2.12; J#4 permanece DONE; próxima = planejar J#5 | [`docs/v2/etapa-j4/`](docs/v2/etapa-j4/) |
| **0.5.49** | J#4 Logistics **DONE**; Blueprint 0.2.11; próxima = planejar J#5 | [`docs/v2/etapa-j4/`](docs/v2/etapa-j4/) |
| **0.5.48** | J#4 Logistics **IN_PROGRESS**; DECs `[PROPOSTA]`; checkpoints I4-0…I4-5 | este arquivo |
| **0.5.47** | Domain-first: ordem de execução J#4 → J#5 → J#3; IDs preservados; Alternativa C (core Ingestion prematuro) rejeitada | este arquivo · Blueprint 0.2.10 |
| **0.5.46** | Slim operacional: remove duplicata layout/runtime/gates genéricos; aponta README/regra/índice | este arquivo |
| **0.5.45** | Gates em `epic-v2.mdc`; DOC_DELTA; gate J#3 = commit operacional do pipeline | regra · docs/README |
| **0.5.44** | docs/README como mapa | [`docs/README.md`](docs/README.md) |
| **0.5.43** | Roadmap operacional; regra unificada; snapshot arquivado | este arquivo · regra |
| **0.5.42** | Inc-6 / Order-to-Pay DONE | [`docs/v2/etapa-inc-6/`](docs/v2/etapa-inc-6/) |
| **0.5.41** | Visual ACCEPTED_WITH_MINOR_BACKLOG; Etapa 9/9V DONE | [`docs/v2/etapa-9v/`](docs/v2/etapa-9v/) |

Changelog integral: [snapshot 0.5.42](docs/v2/archive/roadmap/ROADMAP_V2_EPIC_0.5.42_FULL.md). Índice de documentos: [`docs/README.md`](docs/README.md).
