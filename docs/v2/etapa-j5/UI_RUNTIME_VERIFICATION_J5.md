# Verificação operacional UI J#5

| Campo | Valor |
|---|---|
| Data | 2026-08-04 |
| Método | Browser (Cursor IDE Browser) em `http://127.0.0.1:8082` |
| Screenshots | **Nenhuma** (proibido nesta verificação) |
| Roadmap no início | **0.5.63** |
| Blueprint no início | **0.2.16** |
| Alembic head | **015** (`015_nationalization_inventory`) |
| Branch | `main` |
| Banco | `epic_v2_test` @ `localhost:5433` (ops `epic_v2` **não** tocado) |

## Ambiente

| Item | Valor |
|---|---|
| Backend | uvicorn `app.main:app` · porta **8082** · `DATABASE_URL=…/epic_v2_test` · `APP_ENV=test` |
| Frontend | `frontend/dist` servido pelo FastAPI StaticFiles (build 2026-08-04) |
| Prepare | `scripts/e2e_prepare.py` — schema reset + seed `admin@epic.com.br` |
| Login UI | admin@epic.com.br / admin123 |

## Estado inicial

- Roadmap **0.5.63** — patch fechamento J#5 DONE; próxima = planejar J#3.
- Blueprint **0.2.16** — Alt. B Customs + RECLASS pareado §7.11.
- WIP preservado; sem commit/branch/tag/stash.
- Filas AP/Customs vazias após prepare (antes da massa UIV).

## Objetos utilizados

| Objeto | Código / ID | Origem |
|---|---|---|
| Supplier | `Sup UIV uiverud6u` (id 2) | API (prereq) |
| Product | `SKU-UIV-uiverud6u` — Notebook UIV uiverud6u (id 2) | API (prereq) |
| Order | `ORD-UIV-uiverud6u` (id 2) | API (prereq) |
| Invoices ISSUED | `UIV-uiverud6u-1`, `UIV-uiverud6u-2` (ids 1–2) | API (prereq) |
| Payables EUR | #1 e #2 · EUR 100,00 cada · origem Fatura | API (issue) |
| Shipments | #1 (item qty 6), #2 (item qty 4) | API (prereq) |
| ImportProcess | `IMP-423F7857D74F` · `/customs/1` · DUIMP-UIV-uiverud6u | **UI** |
| Numerário / Payee | #1 Confirmado · Bechtrans-UIV-uiverud6u · BRL 1.500,00 | **UI** |
| Payable CUSTOMS_FUNDING | #3 · BRL 1.500,00 | confirm Numerário (UI) |
| Receipt BONDED | #1 · qty 5 · BONDED-MAIN | **UI** |
| Nationalization | #1 · qty 2 · Confirmada | **UI** |
| Receipt RECLASS | #2 · qty 2 · DOMESTIC-MAIN | **UI** |

API limitada a autenticação + Supplier/Product/Order/Invoice ISSUED/Shipment. Processo, Numerário, receipts, nacionalização e RECLASS = UI.

---

## H-UIV-1 — AP multi-moeda

**Veredito: CONFIRMADA**

| Etapa | URL/tela | Ação realizada pela UI | O que deveria aparecer | O que apareceu efetivamente | Resultado |
|---|---|---|---|---|---|
| 1 | `/payables?pending=OPEN_BALANCE` | Abrir fila sem filtro de moeda | KPIs por moeda; linhas EUR + BRL; sem total único EUR+BRL | KPIs separados: **Saldo aberto (BRL) BRL 1.500,00** e **Saldo aberto (EUR) EUR 200,00**; 3 linhas | **PASS** |
| 2 | mesma | Registrar linhas | moeda/saldo/origem | (1) EUR 100 Fatura; (2) EUR 100 Fatura; (3) BRL 1.500 Numerário / Bechtrans | **PASS** |
| 3 | mesma | Filtrar Moeda=EUR | só EUR; KPIs só EUR | 2 linhas EUR; `kpi-open-balance-EUR` = EUR 200,00; URL `currency=EUR` | **PASS** |
| 4 | mesma | Filtrar Moeda=BRL | só BRL; KPIs só BRL | 1 linha BRL 1.500; `kpi-open-balance-BRL` = BRL 1.500,00; sem linha EUR | **PASS** |
| 5 | mesma | Limpar filtro | ambos de volta; sem default KPI EUR | BRL 1.500 + EUR 200; 3 linhas; URL sem currency | **PASS** |

Valores concretos observados (sem filtro):

- EUR saldo aberto: **EUR 200,00** (2 × 100)
- BRL saldo aberto: **BRL 1.500,00**
- Obrigações: 2 EUR + 1 BRL
- **Não** apareceu EUR 1.700 / 1.900 nem cartão único misturando moedas

Gap residual (não FAIL): placeholder do campo Moeda continua `"EUR"` (hint de input, não KPI).

---

## H-UIV-2 — Drawer Customs

**Veredito: CONFIRMADA**

| Etapa | URL/tela | Ação realizada pela UI | O que deveria aparecer | O que apareceu efetivamente | Resultado |
|---|---|---|---|---|---|
| 1 | `/payables` | Clicar linha `ap-row-3` (Bechtrans) | Drawer Customs | Drawer “Obrigação” aberto | **PASS** |
| 2 | drawer | Observar campos | status/valor/saldo/favorecido/origem/aviso | STATUS **Aberto**; VALOR **BRL 1.500,00**; SALDO **BRL 1.500,00**; FORNECEDOR **Bechtrans-UIV-uiverud6u**; ORIGEM **Numerário (Customs)**; VENCIMENTO **04/08/2026** | **PASS** |
| 3 | drawer | Ações ausentes | sem fatura/cockpit/câmbio/novo pagamento | Ausentes: Abrir fatura, Cockpit, Câmbio da obrigação, Novo pagamento | **PASS** |
| 4 | drawer | Ação presente | Abrir Numerário/processo | Link **Abrir Numerário / processo** → `/customs/funding/1` | **PASS** |
| 5 | click link | Resolver processo | processo + Numerário | URL final **`/customs/1`**; IMP-423F7857D74F; Numerário Confirmado BRL 1.500; payee Bechtrans; **Conta a pagar #3 · Abrir AP** | **PASS** |

Texto do aviso:  
`Obrigação registrada (Numerário) — liquidação via Payment não suportada nesta versão.`

Sem `/invoices/null`, `/orders/null`, 404 ou tela vazia.

---

## H-UIV-3 — Payment Customs

**Veredito: CONFIRMADA**

| Etapa | URL/tela | Ação realizada pela UI | O que deveria aparecer | O que apareceu efetivamente | Resultado |
|---|---|---|---|---|---|
| 1 | drawer Customs | Ler comunicação | obrigação registrada; sem liquidação Payment | Texto exato do aviso (acima); sem CTA Novo pagamento | **PASS** |
| 2 | `/payables` drawer `ap-row-1` | Payable comercial EUR | ações comerciais | Abrir fatura; Cockpit do pedido; Câmbio da obrigação; Novo pagamento — **presentes**; sem aviso Customs | **PASS** |

---

## H-UIV-4 — SC-10 completa

**Veredito: CONFIRMADA**

| Etapa | URL/tela | Ação realizada pela UI | O que deveria aparecer | O que apareceu efetivamente | Resultado |
|---|---|---|---|---|---|
| 1 | `/customs/1` | Receipt BONDED_IN 5 em BONDED-MAIN + confirmar | Confirmado | `#1 · Entrada entreposto · Confirmado · BONDED-MAIN · 1 linhas` | **PASS** |
| 2 | `/inventory/sku/2` | Abrir posição | bonded=5; available=0 | Disponível **0**; Entreposto **5**; Quarentena **0**; Liberado não recebido **0** | **PASS** |
| 3 | `/customs/1` | Liberação qty 2 + confirmar | Confirmada; sem criar disponível | `#1 · Confirmada · … [SKU 2 qty=2]` | **PASS** |
| 4 | `/customs/1` | RECLASS → DOMESTIC-MAIN qty 2 + confirmar | Confirmado | `#2 · Reclassificação · Confirmado · DOMESTIC-MAIN` | **PASS** |
| 5 | `/inventory/sku/2` | Posição final + reabrir | bonded 3 / avail 2 / cleared 0 / físico 5 | Disponível **2**; Entreposto **3**; Quarentena **0**; Liberado não recebido **0** | **PASS** |
| 6 | reload `/inventory/sku/2` | Persistência | mesmos valores | Mesmos valores após nova navegação | **PASS** |

Tabela de conservação:

| Momento | Disponível | Entreposto | Quarentena | Em liberação | Liberado não internalizado | Total físico |
|---|---|---|---|---|---|---|
| Após BONDED 5 | 0 | 5 | 0 | Não disponível | 0 | **5** |
| Após nat 2 + RECLASS 2 (final UI) | 2 | 3 | 0 | Não disponível | 0 | **5** |

Observação: snapshot intermediário “só após nat” não foi reaberto na UI antes do RECLASS; o estado pós-RECLASS e o ledger confirmam que a nat não criou disponível e que o RECLASS reduziu entreposto.

---

## H-UIV-5 — Movimentações

**Veredito: CONFIRMADA**

| Etapa | URL/tela | Ação realizada pela UI | O que deveria aparecer | O que apareceu efetivamente | Resultado |
|---|---|---|---|---|---|
| 1 | `/inventory/movements?product_id=2` | Abrir ledger | BONDED_IN + RECLASS_OUT/IN | 3 linhas (abaixo) | **PASS** |
| 2 | mesma | Identificação humana | SKU/local/regime/tipo pt-BR | Sem `Local #` / `SKU #` | **PASS** |

Linhas observadas:

| Quando | Produto | Local | Regime | Tipo | Δ |
|---|---|---|---|---|---|
| 04/08/2026 11:50:08 | SKU-UIV-uiverud6u — Notebook UIV uiverud6u | DOMESTIC-MAIN | Doméstico | Reclassificação (entrada) | 2 |
| 04/08/2026 11:50:08 | SKU-UIV-uiverud6u — Notebook UIV uiverud6u | BONDED-MAIN | Entreposto | Reclassificação (saída) | -2 |
| 04/08/2026 11:49:33 | SKU-UIV-uiverud6u — Notebook UIV uiverud6u | BONDED-MAIN | Entreposto | Entrada entreposto | 5 |

Pareamento RECLASS: +2 DOMESTIC e −2 BONDED → líquido físico 0 na reclass; total físico permanece 5.

---

## H-UIV-6 — SkuPosition

**Veredito: CONFIRMADA**

| Etapa | URL/tela | Ação realizada pela UI | O que deveria aparecer | O que apareceu efetivamente | Resultado |
|---|---|---|---|---|---|
| 1 | `/inventory/sku/2` | Ler seções | 3 grupos dimensionais | Títulos: **Posição física**, **Situação aduaneira**, **Situação logística** | **PASS** |
| 2 | mesma | Nota de não-aditividade | aviso explícito | “Os grupos abaixo são dimensões diferentes e não devem ser somados entre si. A conservação física vale apenas para Disponível + Entreposto + Quarentena.” | **PASS** |
| 3 | mesma | Stubs | Não disponível | Em liberação / Em trânsito / Pedido futuro = **Não disponível** (não “0”) | **PASS** |
| 4 | mesma | Sem jargão | sem Buckets/deferred/… | Ausentes | **PASS** |

Label UI “Liberado não recebido” ≡ cleared_not_received (equivalente aceitável a “Liberado ainda não internalizado”).

---

## H-UIV-7 — Identificação operacional

**Veredito: CONFIRMADA**

| Etapa | URL/tela | Ação realizada pela UI | O que deveria aparecer | O que apareceu efetivamente | Resultado |
|---|---|---|---|---|---|
| 1 | SkuPosition | Título | SKU + descrição | `SKU-UIV-uiverud6u — Notebook UIV uiverud6u` | **PASS** |
| 2 | Movimentações | Colunas | local code + regime | BONDED-MAIN/DOMESTIC-MAIN + Entreposto/Doméstico | **PASS** |
| 3 | Movimentações | Busca por SKU | filtrar por código | `q=SKU-UIV-uiverud6u` → 3 linhas do produto | **PASS** |

Processo: referência `IMP-423F7857D74F` / DUIMP visível no detalhe Customs (contexto operacional do receipt).

---

## H-UIV-8 — Reload e consistência

**Veredito: CONFIRMADA**

| Etapa | URL/tela | Ação realizada pela UI | O que deveria aparecer | O que apareceu efetivamente | Resultado |
|---|---|---|---|---|---|
| 1 | SkuPosition pós-RECLASS | Reabrir URL | bonded 3 / avail 2 | Persistiu | **PASS** |
| 2 | AP drawer Customs | Reabrir fila | aviso + ações ausentes | Confirmado em H-UIV-2/3 | **PASS** |
| 3 | funding redirect | Deep-link | `/customs/1` estável | OK | **PASS** |

---

## Erros de console e rede

| Tipo | Observação |
|---|---|
| Console errors | Nenhum capturado no harness de verificação (`window.__uivErrors` vazio; sem falha de tela) |
| Network 4xx/5xx | Nenhuma falha material observada nas jornadas (AP, Customs, Inventory carregaram; funding redirect 200) |
| 404 / null routes | Não ocorreram |

---

## Correções realizadas

**Nenhuma.** Comportamento visual/operacional alinhado ao patch; sem defeito delimitado exigindo fix nesta verificação.

Gap residual documentado (não corrigido — fora de blocker):

- Placeholder do filtro Moeda na AP = `"EUR"` (hint de formulário; KPIs não usam default EUR).

---

## Testes e resultados

| Suite | Resultado | Contagem / nota |
|---|---|---|
| pytest Reporting/Billing/Treasury/Customs i5-3b/Inventory/arch | **PASS** | **55** — `logs/uiv-pytest.txt` |
| OpenAPI drift | **PASS** | client up to date — `logs/uiv-api-drift.txt` |
| Vitest inventory + billing | **PASS** | **8** — `logs/uiv-vitest.txt` |
| TypeScript `tsc --noEmit` | **PASS** | `logs/uiv-tsc.txt` |
| build (`tsc` + vite) | **PASS** | `logs/uiv-build.txt` |
| e2e:j5 | **PASS** | **4** — `logs/uiv-e2e-j5.txt` |
| e2e:inc-6 | **PASS** | **1** — `logs/uiv-e2e-inc6.txt` |
| e2e:logistics | **PASS** | **4** — `logs/uiv-e2e-logistics.txt` |

---

## Gaps residuais

1. Placeholder `EUR` no input de moeda da AP (cosmético).
2. Snapshot UI intermediário “apenas após nacionalização” não reaberto antes do RECLASS (estado final + ledger suficientes).
3. Filtro de movimentos por `product_id` mostra o valor numérico `2` no campo até busca por SKU textual.

---

## Veredito

| Hipótese | Veredito |
|---|---|
| H-UIV-1 | **CONFIRMADA** |
| H-UIV-2 | **CONFIRMADA** |
| H-UIV-3 | **CONFIRMADA** |
| H-UIV-4 | **CONFIRMADA** |
| H-UIV-5 | **CONFIRMADA** |
| H-UIV-6 | **CONFIRMADA** |
| H-UIV-7 | **CONFIRMADA** |
| H-UIV-8 | **CONFIRMADA** |

**Veredito final: PASS**

Roadmap permanece **0.5.63**; J#5 DONE; próxima ação = **planejar J#3**.
