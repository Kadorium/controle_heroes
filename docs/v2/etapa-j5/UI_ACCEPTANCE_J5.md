# UI Acceptance — J#5 (patch fechamento)

| Campo | Valor |
|---|---|
| Data | 2026-08-04 |
| Viewport | 1366 × 900 |
| Suite | `npm run e2e:j5` → `e2e/j5-acceptance.spec.ts` |
| Classificação | **ACCEPTED_WITH_BACKLOG** |
| SC cobertos | SC-07, SC-09, SC-10 |
| Roadmap | **0.5.63** |
| Blueprint | **0.2.16** |

## Object codes

| Código | Objeto |
|---|---|
| SCR-019 | Lista Processos Aduaneiros |
| SCR-022 | Detalhe ImportProcess (vínculos, Doganale, Numerário, Liberações, Recebimentos, Docs, Audit) |
| SCR-008 | Contas a pagar (AP) — Payable origem CUSTOMS_FUNDING |
| SCR-024 | Posição SKU (dimensional) |
| SCR-025 | Movimentos de estoque |

## Matriz de screenshots

| Screenshot | Jornada | Estado | Requisitos | Resultado |
|---|---|---|---|---|
| `j5-01-process-list.png` | SCR-019 listagem | ≥1 processo com DUIMP | lista + KPI shell | **PASS** |
| `j5-02-process-links.png` | SCR-022 vínculos | 2 invoices + 2 shipments linked | DEC-DUIMP-MULTI-SHIP / SC-07 | **PASS** |
| `j5-03-item-allocations.png` | Alocações parciais | inv qty=4 / shp qty=3 | residual parcial | **PASS** |
| `j5-04-process-submitted.png` | Submit | status SUBMITTED | lifecycle DRAFT→SUBMITTED | **PASS** |
| `j5-05-doganale-v1.png` | Doganale | v1 ACTIVE com linhas | versionamento | **PASS** |
| `j5-06-doganale-v2-history.png` | Doganale supersede | v2 current + v1 SUPERSEDED | histórico | **PASS** |
| `j5-07-doganale-divergence.png` | Divergência | mensagem visível | rastreio | **PASS** |
| `j5-08-funding-request.png` | Numerário | payee Bechtrans-like + header | fixture Numerário / SC-07 | **PASS** |
| `j5-09-funding-composition.png` | Composição | bases/tax/expense; totais | structured = declared | **PASS** |
| `j5-10-customs-payable-ap.png` | AP | KPIs por moeda; drawer Customs sem liquidação; notice Alt. B | H-J5C-1/2/3 | **PASS** |
| `j5-11-bonded-receipt.png` | Recebimento | BONDED_IN Confirmado qty 5 | SC-10 bonded pré-nac | **PASS** |
| `j5-12-partial-nationalization.png` | Liberação | Confirmada qty 2 | SC-09 | **PASS** |
| `j5-13-sku-position.png` | SCR-024 | bonded 3 / available 2 / cleared 0; dimensões; stubs “Não disponível” | SC-10 conservação | **PASS** |
| `j5-14-inventory-movements.png` | SCR-025 | BONDED_IN + RECLASS_OUT/IN; locais legíveis | ledger append-only | **PASS** |
| `j5-15-documents-audit.png` | Docs + Audit | PDF anexado + tabela audit | Documents/Audit | **PASS** |

Paths: `docs/v2/etapa-j5/screenshots/`.

## Classificação financeira Customs

| Artefato | Estado |
|---|---|
| Core domain J#5 (I5-0…I5-6, mig 011–015) | **DONE** |
| Patch corretivo (C0…C5) | **DONE** |
| Fluxo financeiro Customs (liquidação) | **PARTIAL** |
| UI J#5 | **ACCEPTED_WITH_BACKLOG** |

## Backlog (não minor)

| ID | Item | Destino |
|---|---|---|
| BL-J5-TREASURY | **`Treasury settlement for CUSTOMS_FUNDING`** — Payment/Allocation Customs; counterparty Payee; lifecycle ISSUED/SETTLED | Treasury |
| BL-J5-SEED | Sem usuário seed dedicado `aduana`/`estoque` (roles existem) | Identity sob demanda |
| BL-J5-STUB | Stubs SkuPosition (`in_clearance` / `in_transit` / `future_order`) | Reporting / Logistics |

## Veredito

**ACCEPTED_WITH_BACKLOG** — jornadas SC-07/09/10 (incluindo RECLASS conservativo) demonstradas em E2E; Payable Customs isolado (Alt. B); KPIs multi-moeda sem soma nominal; backlog de liquidação Treasury nomeado.
