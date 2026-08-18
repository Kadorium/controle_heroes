# Cadeia elos 4–6 — Advisor Handoff

| Campo | Valor |
|---|---|
| Etapa | Campanha **elos 4–6** + hardening **C46-HARDEN** |
| Status | **DONE** |
| Data | **2026-08-14** |
| Roadmap | **0.5.118** — cadeia **6/10 = 60%** (inalterada); elos 4–6 **LIGADO / PRONTO** |
| Blueprint | **0.2.22** (invariantes C46-HARDEN) |
| Alembic | **025** (intocado) |
| Portão | **Não iniciar elo 7.** Aguardar autorização. Fora: B0 / J#6 / J#5-REC / Dashboard / backlog adjacente |
| Runtime | UI destrutiva em `:8082` / `epic_v2_test`. `:8081` / `epic_v2` **não** mutado |
| Preservado | Pedido **589** id **31** e **TESTE-CICLO-001** id **34** em `epic_v2` |

---

## Resposta executiva

1. A compra de ensaio anda até o packing virar volumes: crédito + saldo quitam a fatura; qty faturada zera o disponível; Packing List Detail preenche um embarque **planejado** (modal nulo).
2. Identidade do pedido **nunca** é o número do PDF. O operador confirma o Order (0 / 1 / N). Packing não exige fatura prévia.
3. Logistics existente foi **reutilizado** (APIs públicas). Ingestion só orquestra. Grouped não é fonte dos volumes.
4. **C46-HARDEN (2026-08-14):** a mesma história 1→6 foi percorrida **numa massa nova**, pela UI servida, ponta a ponta. Packing já commitado comunica o embarque após reload. IR **DRAFT** = extração editável, não packing pendente. O embarque criado pelo packing tem auditoria. O aviso de palete é factual.
5. **Não** iniciar elo 7 (chegada / declaração / impostos).

---

## Denominadores (Contrato A↔B item 7)

Nenhum `d` mudou neste hardening. Barras **inalteradas**.

| Barra | n | d | % | Motivo |
|---|---|---|---|---|
| Cadeia | 6 | 10 | 60 | Elos 1–6 PRONTO (já em 0.5.117) |
| Ingestão | 3 | 7 | 43 | Inalterado |
| Logística | 2 | 2 | 100 | Inalterado |
| Financeiro / Aduana / Custo / Painel | — | — | — | Inalterados |

---

## C46-HARDEN

Objetivo: elevar 1→6 de “funcional e provada por fases” para jornada operacional integral, persistente, auditável e profissional pela UI.

### Hipóteses

| ID | Hipótese | Resultado |
|---|---|---|
| H1 | Aceite 1→6 deve ser uma história só, pela UI, com massa nova | **Confirmada** — walk 20 passos em `epic_v2_test` (`C46-H1-328`, Order **#1**) |
| H2 | Servidor idempotente; UI pós-commit era efêmera | **Confirmada** — preview deriva `IngestionCommitAttempt` SUCCEEDED; banner “Packing processado — Embarque #X”; sem segundo Shipment |
| H3 | DRAFT após commit é bug de domínio | **Refutada** — `review_status` DRAFT = extração ainda editável; commit **não** muda o ciclo do IR. Só linguagem na UI |
| H4 | “Sem eventos de auditoria” no Shipment do packing | **Confirmada como gap** — packing chama `logistics.public`; audit passou para os comandos públicos (não log paralelo). UI passou a listar 5 eventos |
| H5 | Paletes declarados 1 vs PALLET derivados 0 é parse errado | **Refutada** — 5 CARTON no detalhe; 1 palete no cabeçalho. Mensagem operacional; **não** bloqueia commit |

### Alterações (código)

- Preview/commit Packing **e** Fattura: `already_committed` + banner persistente + esconde commit; idempotência por `document_id` (não só `operation_key`).
- Linguagem IR: “Revisão da extração · extração ainda editável”; hint de que o status das seções **não** indica packing/fatura pendente.
- Logistics: `actor_id` opcional nos comandos públicos; packing passa o ator do commit. Labels de ação no detalhe do embarque.
- Aviso de palete: “O documento declara N palete(s), mas os volumes detalhados importados são M caixa(s) e nenhum volume do tipo PALLET…”.
- Cópia: removidos “Cartons 4819” e “tentativa #<id global>” do fluxo principal.

### Walk UI 1→6 (2026-08-14, `:8082` / `epic_v2_test`)

Massa canônica nova após schema pós-pytest. Login operador. Corpus **328**.

| # | Passo | Runtime / DB | Abri / Vi / Cliquei | Resultado |
|---|---|---|---|---|
| 1–2 | Order disponível + confirmar | `:8082` · Order **#1** | `/orders/new` — Heroe's Srl, SKU `8057628953593`, 50 @ 106,66 | Confirmado · total EUR 5.333,00 · `h1-01-order-confirmed.png` |
| 3 | ADVANCE | Payment crédito no pedido | Comercial → 1250 EUR, taxa 5,9759, datas 2026-05-18, sem PDF (admin) | EUR 1.250,00 → BRL 7.469,88 |
| 4–7 | Fattura → Invoice DRAFT | IR doc **#1** · Invoice **#1** | `/ingestion` → PDF 328 → Fattura Heroes → confirmar Order #1 → Commit | SUCCEEDED · policy A · scadenze 1250+4083 |
| 8–9 | Condições + emitir | Invoice ISSUED · 2 Payables | `/invoices/1` · Emitir | Emitida · obrigações 18/05 e 31/07 |
| 10–13 | Payables + crédito + SETTLEMENT | Payables **#1 PAID**, **#2 PAID** | Câmbio parcela 1 → aplicar ADVANCE; parcela 2 → Novo pagamento 4083 → alocar | Saldos EUR 0,00 · cockpit Pago 5.333 |
| 14 | Pedida / Faturada / Disponível | qty API no comercial | `/orders/1/commercial` tabela `invoiced-qty` | **50 / 50 / 0** · `h1-14-pedida-faturada.png` |
| 15–17 | Packing importar + confirmar + commit | IR doc **#2** · Shipment **#1** | PDF Packing List → packing_list_detail_v1 → Order #1 → Commit | 5 CARTON · qty 50 · banner “Packing processado” · `h1-packing-committed.png` |
| 18–19 | Shipment + packages/contents | 1 shipment, 5 packages, 5 contents | `/shipments/1` · Conteúdo vol. #1 | Planejado · 10 un · NCM `95069900` · `h1-shipment-1.png` |
| 20 | Persistência | mesmos IDs | Reload `/ingestion/2`; 2º POST commit com outra `operation_key` | Banner permanece; commit escondido; **1** shipment; attempt id=2 reutilizado |

**H2 reload:** seções header/cartons/annotations continuam PENDING/DRAFT **com** o texto de que isso não significa packing pendente. Banner e link do embarque vêm do servidor, não do React da sessão.

**H4:** `audit_log` — `shipment.create`, `item.add`, `packages.add`, `reference.add`, `summary.upsert` (5 linhas, `entity_id=1`).

**H5:** “O documento declara 1 palete(s), mas os volumes detalhados importados são 5 caixa(s) e nenhum volume do tipo PALLET… Isso não impede o embarque.” Totais: PALETES 0, CAIXAS 5.

### API ainda usada e justificativa

| Uso | Justificativa |
|---|---|
| Injetar PDF no `<input type=file>` via `DataTransfer` (bytes servidos em `/assets` só para o MCP) | Limitação da ferramenta: o seletor nativo de ficheiros é bloqueado. **Não** é gap de produto — o operador usa a dropzone. Classify / adapter / commit / emitir / pagar = cliques na UI |
| 2º POST `commit-pl-detail` com `operation_key` nova | Prova de idempotência (o botão de commit já estava escondido) |
| GET de inspeção | Verificação |
| Catálogo + Order | **UI** (`/orders/new`, criar SKU e fornecedor no formulário) |

Nenhuma ação operacional do percurso 1→20 ficou só na API.

### Testes

- pytest packing/logistics/a0/arch + **suite V2 555 passed** (antes do walk; `drop_all` — **não** relançar até o walk fechar)
- Vitest C4–C6 + packing/fattura banners persistentes: PASS (incl. 6 testes painel após cópia 4819)
- `check:api-drift`: OpenAPI alinhado (preview `already_committed`)
- `tests/architecture/test_import_boundaries.py`: PASS
- Idempotência: 2º commit → mesmo attempt SUCCEEDED, 1 shipment, 5 packages

### `docs/README.md`

A linha da timeline Cadeia 4–6 no CF anterior é **índice legítimo** (mapa documental). Preservada; atualizada para 0.5.118 / Blueprint 0.2.22.

### Pendências (não bloqueiam DONE)

- Editor genérico do IR ainda mostra JSON bruto nas “Linhas” (há Campos estruturados acima).
- Policy A/B/C1/C2 e digest hex no preview Fattura (fluxo avançado, não redesenhado).
- Evidência de câmbio do SETTLEMENT 4083 não registada (admin sem PDF); obrigação **PAID** na mesma.
- “Quem” na auditoria do embarque mostra o id do ator (`1`), não o nome.
- Pytest contra `epic_v2_test` apaga esta massa H1.

Fora de escopo: elo 7+, B0, J#6, Dashboard, ACCONTO, auto-allocation, BOOKED a partir do packing, Grouped como SoT.

---

## Estado anterior → atual

| | 0.5.117 (campanha) | 0.5.118 (hardening) |
|---|---|---|
| Cadeia | 6/10; elos 1–6 PRONTO por fases | 6/10 **inalterada**; jornada 1→6 **numa** história UI |
| Packing pós-commit | Banner some no reload | Banner persistente + link embarque |
| IR DRAFT | Dúvida de produto | Contrato: extração editável ≠ packing pendente |
| Auditoria embarque | “Sem eventos” | 5 eventos nos comandos Logistics |
| Palete | Warning numérico | Mensagem operacional factual |

---

## Hipóteses da campanha (0.5.117)

| ID | Hipótese | Resultado |
|---|---|---|
| H-C4 | Zero domínio novo; costura ADVANCE→SETTLEMENT no mesmo pedido da Fattura | **Confirmada** |
| H-C5 | Pedida/Faturada/Disponível + overbill; B0 desnecessário | **Confirmada** |
| H-C6-PARSE | Texto default do adapter perde cartons; layout tem 5×10 | **Confirmada** |
| H-IDENTITY | Pedido ≠ número do documento | **Confirmada** |
| H-PLANNED | `modal=null`; não BOOKED | **Confirmada** |
| H-SOT | Detail preenche; Grouped não | **Confirmada** |
| H-IDEM | Documento já SUCCEEDED não duplica | **Confirmada** (reforçada no H2) |

---

## Gates por fase

| Fase | Gate | Evidência |
|---|---|---|
| P0 | Runtime Teste + amostra | [`P0_RUNTIME.md`](P0_RUNTIME.md) |
| C4 | UI ADVANCE → Fattura → crédito → SETTLEMENT | `c4-advance-registered.png`, `c4-cockpit-settled.png` |
| C5 | UI qty + overbill no Emitir | `c5-pedida-faturada-disponivel.png`, `c5-overbill-blocked.png` |
| C6A–C6C | Parse + Logistics + painel | `c6c-*.png` |
| Aceite 1→6 | 1→5 API + packing UI | `aceite16-*.png` |
| **C46-HARDEN** | Walk integral UI 1→6 + H2–H5 | `h1-01-order-confirmed.png`, `h1-14-pedida-faturada.png`, `h1-packing-committed.png`, `h1-shipment-1.png` |

---

## Decisões ratificadas (não reabrir sem produto)

DEC-C6-IDENTITY · INVOICE-OPTIONAL · LINE-MATCH · COMMITMENT · PLANNED-ONLY · DETAIL-SOT · SHIPMENT-TARGET — Blueprint §5.9 / §5.10 / §7.19.

**DRAFT do IR após commit** = extração editável. Não criar estado ad hoc “COMMITTED” no IR só porque o packing/fattura gerou Shipment/Invoice.

---

## Recomendação

Aceitar **0.5.118** (hardening; barras 6/10). Próxima ação = **aguardar autorização**; **não** iniciar elo 7.

---

## Evidências âncora

- Dir: [`docs/v2/etapa-cadeia-46/`](.)
- Plano mestre: `cadeia_elos_4-6_e4ef4c0f.plan.md`

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/README.md; docs/v2/etapa-cadeia-46/CADEIA_46_ADVISOR_HANDOFF.md; docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md (0.2.22, rodada anterior deste hardening)
- Evidence: docs/v2/etapa-cadeia-46/
- Roadmap status: 0.5.117 DONE 6/10 → 0.5.118 hardening C4–C6; barras inalteradas. A/B: A.0 data+última entrega; A.3 packing persistente; B.1 versão; B.2 elo 6; B.4; B.7
- Next TODO: não iniciar elo 7; aguardar autorização
- Return to advisor: docs/v2/etapa-cadeia-46/CADEIA_46_ADVISOR_HANDOFF.md
```
