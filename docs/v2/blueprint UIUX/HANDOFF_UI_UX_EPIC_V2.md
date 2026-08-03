# Epic Controle V2 — Handoff UI/UX (pacote operacional)

```text
Versão handoff: 1.0
Status: HISTÓRICO DE EXECUÇÃO — Etapa 8 (CONSOLIDADO)
Data: 2026-07-29
Etapa: 8 — DONE (E8-A APROVADO COM AJUSTES · E8-B APROVADO)
Natureza: artefato histórico de execução da Etapa 8 — NÃO é autoridade de domínio
         nem substitui o Blueprint UI/UX. Status de implementação atual: consultar o Roadmap.
Não é implementação. Sem React/CSS. Sem inventar contratos.
```

### Autoridades (precedência)

| Assunto | Autoridade |
|---|---|
| Domínio, entidades, cardinalidades, ownership, invariantes | Blueprint Sistema |
| Estado, gates, versões, evidências de fase | **Roadmap** (status atual — consultar o arquivo vigente; pin 0.5.27 abaixo = histórico desta sync) |
| Arquitetura de informação, superfícies, fluxos, Design System | Blueprint UI/UX **v3.10** (referência de design) |
| Evidência visual Horizon A | MCK **v1.1** |
| Interpretação do MCK | cenário, direção visual, legenda, auditorias E6 |
| Código / contratos runtime reais | código em `v2/` · status de superfícies no Roadmap |

### Invariantes de domínio (Sistema §6.2–§6.3 — citar, não reinterpretar)

- Order **1:N** Invoice  
- Invoice **1:N** Payable  
- Payment **N:M** Payable via **PaymentAllocation**  
- Registrar Payment **não** reduz saldo de Payable  
- Somente **PaymentAllocation** reduz saldo  
- Payable = unidade de liquidação  
- Heroes = único fornecedor operacional atual (UX sem ênfase multi-fornecedor)  
- FX planejado / mercado / realizado permanecem distintos  
- Cockpit = read model somente leitura  

### Changelog

| Rev | Data | Notas |
|---|---|---|
| 0.1 | 2026-07-29 | Etapa **8A** — handoff candidato; E8-A pendente revisão externa |
| 1.0 | 2026-07-29 | Etapa **8B** — consolidação: assets com paths reais; permissões sem wildcards; taxonomia; SCR-011 comprovante; evidências com documento; D-DOC-01 ACEITA; DoR fechado; E8-A aprovado com ajustes (concluídos); E8-B APROVADO |

---

## 1. Índice de autoridades e artefatos

| Artefato | Versão | Caminho | Papel | Autoridade | Consultar | Não inferir | Precedência | Vigência |
|---|---|---|---|---|---|---|---|---|
| Blueprint Sistema | 0.2.8 | `docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md` | Domínio canônico | Sim (domínio) | Cardinalidades, owners, DEC abertas, Heroes | Layout visual, tokens CSS | Vence em domínio | Vigente |
| Roadmap V2 | (consultar vigente) | `ROADMAP_V2_EPIC.md` | Estado/gates | Sim (governança) | Status fases; implementação de superfícies | Spec de tela | Vence em status | Vigente no arquivo na raiz; pin 0.5.27 nesta sync = histórico |
| Blueprint UI/UX | 3.10 | `docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md` | IA, SCR, FLW, DS | Sim (UX/DS) | UI/UX §20–§27, §21, §23–§24 | Runtime não documentado | Vence em UX/DS | Vigente candidato |
| MCK | 1.1 | `docs/v2/blueprint UIUX/mockups/mck-v1.1/` | Evidência visual | Sim (visual) | SVG/PNG/PDF/smoke | Comportamento API | Sob DS UI/UX §26–§27 | Vigente |
| Cenário canônico | 1.1 | `docs/v2/blueprint UIUX/mockups/mck-v1.1/CANONICAL_SCENARIO.md` | Valores T0–T3 | Interpretação | Momentos; valores fictícios | Dados de produção | Sob MCK | Vigente |
| Direção visual | 1.1 | `docs/v2/blueprint UIUX/mockups/mck-v1.1/VISUAL_DIRECTION.md` | Família visual | Interpretação | Cores/tipografia MCK | Tokens formais (UI/UX §26) | Sob UI/UX §26 | Vigente |
| Legenda MCK | 1.1 | `docs/v2/blueprint UIUX/mockups/mck-v1.1/annotations/MCK-v1.1-legend.md` | Correções 6B | Interpretação | E6-001…E6-018 | **Versão UI/UX citada (v3.9) = histórica** — vigente = v3.10 (D-DOC-01 ACEITA) | Não vence cabeçalho UI/UX | Vigente c/ D-DOC-01 |
| E6B change-log | 1.1 | `docs/v2/blueprint UIUX/mockups/mck-v1.1/annotations/E6B-change-log.md` | Diff 6B | Interpretação | Correções visuais | DS normativo | Sob MCK | Histórico útil |
| E6A audit | 1.0 | `docs/v2/blueprint UIUX/mockups/mck-v1.0/annotations/E6A-visual-audit.md` | Achados 6A | Interpretação | Achados E6-* | Estado pós-6B | Sob MCK v1.1 | Histórico |
| Este handoff | 1.0 | `docs/v2/blueprint UIUX/HANDOFF_UI_UX_EPIC_V2.md` | Rastreabilidade | **Não** (operacional) | Fichas, matrizes, gaps, DoR | Domínio novo; endpoints não documentados | Abaixo das autoridades | Consolidado |
| Roteiro redesenho | — | `docs/v2/blueprint UIUX/Roteiro do redesenho UIUX.txt` | Sequência etapas | Orientação | Escopo Etapa 8/9 | Spec detalhada | Sob Roadmap/UI/UX | Vigente |
| docs/README | — | `docs/README.md` | Índice | Ponteiro | Links | Spec | — | Vigente |

### 1.1 Divergências documentais reais

| ID | Descrição | Autoridade | Tratamento |
|---|---|---|---|
| **D-DOC-01** | Legenda MCK cita “UI/UX **v3.9**”; vigente = **v3.10** | Cabeçalho UI/UX / Roadmap | **ACEITA** — referência histórica ao UI/UX v3.9; a autoridade vigente é UI/UX v3.10. Nenhuma alteração no artefato histórico. |

Não há outras contradições documentais materiais comprovadas entre Sistema 0.2.8, UI/UX v3.10 e Roadmap vigente neste pacote.

### 1.2 Diferenças AS-IS versus TARGET (intencionais — não são “divergências”)

| Tema | AS-IS | TARGET | Classificação |
|---|---|---|---|
| Grupos nav | Ordens · Financeiro (Faturas sob Financeiro) | Compras (Pedidos+Faturas) · Financeiro | `AS_IS` / `TARGET` |
| Tema visual | Shell/frontend escuro densificado | Light navy MCK + UI/UX §26 | `AS_IS` / `TARGET` |
| Hub Câmbio | SCR-009 + strip | Item SCR-028 `/fx` | `TARGET` + `GAP_TECNICO` + `FORA_HORIZON_A` operacional |
| Login redirect | Sempre `/orders` | `?next=` interno | `TARGET` + `GAP_TECNICO` |
| AP → Payment | Link sem query | Query contextual | `GAP_TECNICO` (G02) |
| Retorno filas | Parcial | Query + linha + scroll | `TARGET` + `GAP_TECNICO` parcial |

### 1.3 Taxonomia de classificação (canônica neste handoff)

`AS_IS` · `TARGET` · `GAP_TECNICO` · `DECISAO_ABERTA` · `DEFERRED_RUNTIME` · `FORA_HORIZON_A`

Coluna aparte: **Validação Etapa 9:** `NECESSARIA` | `NAO_NECESSARIA`

---

## 2. Fichas Horizon A (SCR-001…012)

Convenção de campos (25): ver brief Etapa 8A. Endpoints/perms só se já constarem de UI/UX §21 / Sistema / Roadmap.

---

### SCR-001 — Login

1. **ID/nome:** SCR-001 Login  
2. **Pergunta:** Quem sou eu e posso entrar?  
3. **Rota TARGET:** `/login` (sem App Shell)  
4. **Rota AS-IS:** `/login`; pós-auth → `/orders`  
5. **Entidade/RM:** Session / Identity  
6. **Owner superfície:** identity (FE auth)  
7. **Owners domínio/dados:** Identity  
8. **Perfis:** admin, comprador (roles AS-IS documentados)  
9. **Permissões:** autenticação; sem shell RBAC  
10. **Estados:** loading submit · erro credencial · rede · sessão válida/expirada · submit duplicado (§21.0/§21.1)  
11. **Ação primária:** Entrar  
12. **Secundárias:** —  
13. **Perigosa:** —  
14. **Dados obrigatórios:** e-mail/usuário · senha  
15. **Opcionais:** —  
16. **Vazio≠zero:** N/A valores financeiros  
17. **Componentes DS:** Button primary; Input; Notice/Error  
18. **Composição:** página centrada marca + formulário (§21.1 wire)  
19. **Referência visual:** **ANALOGA_SUFICIENTE** — sem artboard exclusivo. Inferir de UI/UX §21.1 + marca/shell navy dos MCK (sidebar brand). **Artboard:** nenhum Login; **reuso:** tipografia/cores UI/UX §26 + layout wire. **Inferível:** hierarquia form, CTAs, ausência de shell. **Não inferível:** pixel-perfect login, microcopy final além de UI/UX §21.1. **Aceite:** sem shell; sem credencial em URL; mensagem genérica em falha; sem tratar `?next=` como AS-IS.  
20. **Fluxos:** entrada; 401 → login (FLW-007)  
21. **Erros:** credencial inválida; rede + retry; redirect só paths internos  
22. **Responsividade:** full page; UI/UX §26.8 N/A fila  
23. **A11y:** labels; foco no erro; `DEFERRED_RUNTIME` SR  
24. **Gaps/DEC/aceite:** `?next=` = `GAP_TECNICO`; Validação E9: NECESSARIA (wiring). Aceite UI/UX §21.1.  
25. **Evidência:** UI/UX §21.1 · UI/UX §20.7  

**Suficiência visual:** ANALOGA_SUFICIENTE — revalidada 8B. Ref. normativa UI/UX §21.1; visual análogo = wire UI/UX §21.1 + marca/shell navy dos MCK (sem artboard Login). Inferível: hierarquia form, CTAs, ausência de shell. Não inferível: pixel-perfect login. Aceite: sem shell; sem credencial em URL; falha genérica; `?next=` não é AS-IS.

---

### SCR-002 — App Shell

1. **SCR-002 App Shell**  
2. Chrome global: onde estou e para onde posso ir?  
3. TARGET: chrome em todas rotas autenticadas; grupos Compras \| Financeiro  
4. AS-IS: Ordens \| Financeiro (Faturas sob Financeiro)  
5. Nav + RBAC + FX strip  
6. **Owner superfície:** frontend / foundation (apresentação)  
7. **Owners domínio:** nenhum único (agrega Identity + perms de módulos)  
8. Personas orientam; roles AS-IS admin/comprador  
9. Itens ocultos sem perm; strip exige `treasury:fx_read`  
10. Sticky sidebar; 401 redirect login; sem busca global Horizon A  
11. Navegação primária por item  
12. FX refresh (se perm); Admin/Sair  
13. —  
14. Brand · grupos · itens · user  
15. Badge só se API real  
16. —  
17. AppShell · Sidebar · NavItem · FxMarketStrip · PageHeader slot  
18. Sidebar 220 + main inset (§26.5/§27.1)  
19. **DIRETA (transversal):** shell em MCK-001…MCK-007. Inferível: navy, nav, strip, densidades. Não inferível: comportamento runtime de refresh além do documentado.  
20. Todas as superfícies autenticadas  
21. 403 item oculto; strip ausente sem perm  
22. UI/UX §26.8  
23. Landmarks; skip link TARGET; `DEFERRED_RUNTIME`  
24. Nav TARGET vs AS-IS = diferença intencional; SCR-028 não renderizar morto. Aceite UI/UX §20.  
25. UI/UX §20 · UI/UX §27.1 · MCK-001…MCK-007  

**Suficiência visual:** DIRETA (evidência transversal)  

---

### SCR-003 — Pedidos (fila)

1. SCR-003 Pedidos  
2. Onde está o pedido e qual o próximo passo?  
3. `/orders`  
4. `/orders`  
5. Order (`GET /orders?status&limit&offset` AS-IS)  
6. **Owner superfície:** Orders  
7. **Owners dados:** Orders (Catalog para supplier quando exposto)  
8. admin/comprador c/ `orders:read`  
9. `orders:read` · `orders:write` (Nova)  
10. loading · empty · no-results · erro · parcial · 401/403 · preservação TARGET  
11. Abrir cockpit (linha)  
12. Novo pedido  
13. —  
14. Código · data · supplier · status · total · atualizado (AS-IS)  
15. Enrichment TARGET (nome, faturado, saldo, vencimento, pendências) — `GAP_TECNICO` se ausente  
16. Unpriced → total "—" / incompleto; nunca 0 inventado  
17. PageHeader · FilterChip · OperationalTable (density standard) · StatusBadge · MoneyDisplay · Button  
18. Fila search-grid; Código sticky TARGET  
19. **DIRETA — MCK-001** (T0). PDF p.1 · PNG e SVG com paths em §7.  
20. FLW-001 origem; FLW-007 retorno  
21. Erro+retry; 403 empty  
22. Scroll V/H 1366; UI/UX §26.8  
23. Sticky; foco linha; `DEFERRED_RUNTIME`  
24. Enrichment = `GAP_TECNICO`; Validação E9 NECESSARIA. Aceite: linha=Order; lote proibido.  
25. UI/UX §21.2 · UI/UX §25.2 · MCK-001  

**Suficiência visual:** DIRETA  

---

### SCR-004 — Novo pedido

1. SCR-004 Novo pedido  
2. Como crio um pedido rascunho/confirmado?  
3. `/orders/new`  
4. `/orders/new`  
5. Order + OrderItems  
6. **Owner superfície:** Orders  
7. **Owners dados:** Orders · Catalog (SKU/supplier)  
8. `orders:write`  
9. `orders:write`  
10. loading · validação · 403 · 409 · unsaved TARGET · submit duplicado  
11. Salvar DRAFT / Confirmar  
12. Cancelar; add/remove linhas  
13. — (confirm é auditável, não “perigosa” no sentido cancel financeiro)  
14. Código · fornecedor · moeda · data · ≥1 linha SKU+qtd para confirm  
15. Preço (ausente = unpriced)  
16. Preço ausente ≠ 0; total incompleto  
17. PageHeader · Input · Select · Button · MoneyInput · Notice  
18. Form ~1120; sticky actions (UI/UX §21.3)  
19. **ANALOGA_SUFICIENTE** — sem artboard exclusivo. **Artboards análogos:** MCK-003 (form/edit densos) + MCK-005 (form + sticky actions) + shell MCK-001. **Inferível:** densidade form, inputs 32, botões md/lg, PageHeader. **Não inferível:** layout exato de grid de itens do pedido; copy específica além de UI/UX §21.3. **Aceite:** vazio≠0; confirm auditável; sem total falso; SKU duplicado permitido pelo contrato.  
20. FLW-001 (pré); retorno fila FLW-007  
21. Validação campo/global; 409 version → reload  
22. Form arquétipo UI/UX §26.8  
23. Labels; foco erro; unsaved TARGET  
24. Unsaved confirm = TARGET/`GAP_TECNICO` se FE ausente; Validação E9 NECESSARIA.  
25. UI/UX §21.3 · UI/UX §27.4  

**Suficiência visual:** ANALOGA_SUFICIENTE — revalidada 8B (sem AMBIGUIDADE_MATERIAL).  

---

### SCR-005 — Cockpit do pedido

1. SCR-005 Cockpit do pedido  
2. Qual o estado completo deste pedido e para onde ir?  
3. `/orders/:orderId`  
4. Idem; summary se `reporting:read` senão OrderDetailPage  
5. Read model `order_cockpit` / summary  
6. **Owner superfície/RM:** **Reporting**  
7. **Owners dados-fonte:** Orders · Billing · Treasury (somente leitura agregada)  
8. Variantes por `reporting:read`  
9. `reporting:read` (queue/summary); fallback `orders:read`  
10. loading · erro Reporting · 403 · 404 · empty blocos · stale comercial  
11. Deep links para superfícies donas  
12. Toggle fallback comercial  
13. — (**proibido** mutar domínio no cockpit)  
14. Blocos summary conforme contrato Reporting documentado  
15. Docs/Audit listas no summary (limites Reporting)  
16. Blocos vazios = “Nenhuma…” — não zero financeiro  
17. KpiStrip · Notice · AuditDocumentsBlock · Link · StatusBadge · MoneyDisplay  
18. Página convergência + deep links (MCK-002)  
19. **DIRETA — MCK-002** T0  
20. FLW-001/006/007; não FLW mutate  
21. Falha Reporting → ErrorState; TARGET oferecer fallback sem fingir KPI  
22. UI/UX §26.8 full page  
23. Headings seções; `DEFERRED_RUNTIME`  
24. Docs/Audit deep link dedicado = `GAP_TECNICO`; Cockpit RO. Validação E9 NECESSARIA (wiring). Aceite: Reporting não escreve.  
25. UI/UX §21.4 · UI/UX §23.6 · MCK-002 · Sistema §8 (Reporting)  

**Suficiência visual:** DIRETA  

---

### SCR-006 — Faturas (lista)

1. SCR-006 Faturas  
2. Quais faturas existem e qual o status?  
3. `/invoices` (nav TARGET sob Compras)  
4. `/invoices` (AS-IS sob grupo Financeiro)  
5. Invoice (`GET /invoices?order_id&status&limit&offset`)  
6. **Owner superfície:** Billing  
7. **Owners dados:** Billing (Order ref); Catalog/supplier enrichment se existir  
8. `billing:read`  
9. `billing:read` / `billing:write`  
10. loading · empty · no-results · erro · parcial · 401/403  
11. Abrir detalhe  
12. — (create via Order, não `/invoices/new`)  
13. —  
14. Número · tipo PROFORMA\|FINAL · Order · data · moeda · total · saldo · status  
15. Doc; `# Payables`; `supplier_name` — `GAP_TECNICO` se ausente no list item  
16. Gaps → "—" / omitir; ACCONTO não operacional (`DECISAO_ABERTA`)  
17. PageHeader · FilterChip · OperationalTable (standard) · StatusBadge · MoneyDisplay  
18. Search-grid análogo Pedidos  
19. **ANALOGA_SUFICIENTE** — sem artboard exclusivo. **Artboard:** MCK-001 (fila) + shell; wire UI/UX §20 W2. **Inferível:** densidade tabela standard 40, filtros, PageHeader, badges. **Não inferível:** conjunto final de colunas pixel-a-pixel; presença visual de `# Payables` se contrato incompleto. **Aceite:** linha=Invoice; 1 Order por Invoice; sem ACCONTO ativo; lote proibido; create não via lista standalone.  
20. FLW-001/002 retorno; FLW-007  
21. Erro+retry; 403  
22. Scroll H/V; sticky Número TARGET  
23. Como OperationalTable UI/UX §27.3  
24. `supplier_name` / `payable_count` = `GAP_TECNICO` se ausentes; DEC-ACCONTO = `DECISAO_ABERTA`. Validação E9 NECESSARIA.  
25. UI/UX §21.5 · UI/UX §20 (W2)  

**Suficiência visual:** ANALOGA_SUFICIENTE — revalidada 8B (sem AMBIGUIDADE_MATERIAL).  

---

### SCR-007 — Fatura (detalhe)

1. SCR-007 Fatura  
2. Esta fatura está pronta para emitir e o que cria?  
3. `/invoices/:invoiceId`  
4. Idem  
5. Invoice + Terms + itens  
6. **Owner superfície:** Billing  
7. **Owners dados:** Billing; Payables criados na emissão  
8. por ação — ver item 9  
9. `billing:write` · `billing:issue` · `billing:issue_without_doc`  
10. DRAFT editável · ISSUED readonly · CANCELLED; loading · 409 · confirmação  
11. Emitir (DRAFT)  
12. Salvar; docs/audit  
13. Cancelar **somente DRAFT**; override sem doc  
14. Itens · terms · blockers · documento quando exigido  
15. Override flags  
16. Saldo não editável na UI; ausência ≠ 0  
17. PageHeader · Input · Button · StatusBadge · Notice · ConfirmationModal · AuditDocumentsBlock · MoneyDisplay  
18. Header sticky + blockers + ações (MCK-003)  
19. **DIRETA — MCK-003** T0 (+ AUX FLW-002)  
20. FLW-001 destino; FLW-002 emissão  
21. Blockers; rollback UoW; 409 version  
22. Form/full page UI/UX §26.8  
23. Confirmação; foco  
24. Preview Payables TARGET. Aceite: emit só blockers OK ou override; cancel ISSUED ausente.  
25. UI/UX §21.6 · MCK-003 · Sistema §5.7  

**Suficiência visual:** DIRETA  

---

### SCR-008 — Contas a pagar

1. SCR-008 Contas a pagar  
2. O que vence e o que faço agora?  
3. `/payables`  
4. Idem (`ap_queue` ou lista Payable)  
5. `ap_queue` / Payable  
6. **Owner superfície/RM:** **Reporting** (fila enriquecida)  
7. **Owners domínio/dados:** **Billing** (Payable); Treasury/FX complementares quando queue  
8. por ação — ver item 9  
9. `reporting:read` · `billing:read` (fallback) · CTA pagamento `treasury:write`  
10. loading · empty · no-results · erro · parcial · 403  
11. Abrir drawer / detalhe obrigação  
12. Ir a FX; Novo pagamento (TARGET query)  
13. —  
14. Vencimento · saldo · status · invoice/order refs  
15. FX planejado/BRL · KPIs queue  
16. Sem FX no fallback — não inventar; KPI omitidos no fallback  
17. KpiStrip · FilterChip · OperationalTable (`table.density.finance` rowHeight 44) · StatusBadge · DetailDrawer · MoneyDisplay · RateDisplay  
18. Fila + drawer (MCK-004)  
19. **DIRETA — MCK-004** T0  
20. FLW-003/005/007  
21. Fallback sem fingir FX; G02  
22. UI/UX §26.8; densidade financeira (`table.density.finance`)  
23. Drawer Escape `DEFERRED_RUNTIME`  
24. G02 = `GAP_TECNICO`; L-005 = `DECISAO_ABERTA`. Validação E9 NECESSARIA. Aceite: linha=Payable.  
25. UI/UX §21.7 · MCK-004 · Sistema §8 (Reporting / AP)  

**Suficiência visual:** DIRETA  

---

### SCR-009 — Câmbio da obrigação

1. SCR-009 Câmbio da obrigação  
2. Qual taxa planejada, de mercado e executada?  
3. `/payables/:payableId/fx`  
4. Idem  
5. FxPlanRate · FxMarketQuote · FxExecution · valuations  
6. **Owner superfície:** Treasury  
7. **Owners dados:** Treasury (FX); Payable (Billing) como contexto  
8. por ação — ver item 9  
9. `treasury:fx_read` · `treasury:fx_write` · `treasury:fx_quote_refresh` · `treasury:fx_without_document` · `treasury:fx_supersede` (rebind) — UI/UX §21.8  
10. loading · stale/missing quote · 403 · erro refresh  
11. Definir/atualizar plano; refresh quote  
12. Execução; rebind valuation; docs  
13. CORRECTION / rebind (auditado)  
14. Payable context; rate fields conforme contrato doc  
15. History; PnL  
16. Ausência execução = “sem execução”; PnL null = "—" nunca 0  
17. PageHeader · Money/Rate · Notice · Button · AuditDocumentsBlock · Input  
18. Três colunas/visões (MCK-007) — exceção de composição  
19. **DIRETA — MCK-007** T0  
20. FLW-005  
21. Refresh fail; 403 por ação  
22. Workspace UI/UX §26.8  
23. Stale não só cor  
24. SCR-028 hub = `FORA_HORIZON_A` operacional / `GAP_TECNICO`. FX **não** liquida. Aceite UI/UX §21.8.  
25. UI/UX §21.8 · MCK-007 · Sistema §5.8 / §7 (FX)  

**Suficiência visual:** DIRETA  

---

### SCR-010 — Pagamentos (lista)

1. SCR-010 Pagamentos  
2. Quais movimentos financeiros e residual?  
3. `/payments`  
4. Idem  
5. Payment (`GET /payments` com filtros documentados incl. `unallocated_only`, `limit`, `offset`)  
6. **Owner superfície:** Treasury  
7. **Owners dados:** Treasury  
8. `treasury:read`  
9. `treasury:read` · `treasury:write` (Novo)  
10. loading · empty · no-results · erro · parcial · 403  
11. Abrir detalhe  
12. Novo pagamento  
13. —  
14. Data · ref · supplier · moeda · valor · alocado · residual · status  
15. FX/doc se presentes; senão parcial  
16. Residual explícito; unallocated destacado  
17. PageHeader · FilterChip · OperationalTable (standard) · StatusBadge · MoneyDisplay · Button  
18. Search-grid análogo Pedidos  
19. **ANALOGA_SUFICIENTE** — sem artboard exclusivo. **Artboard:** MCK-001 (fila) + shell; wire UI/UX §20 W4; residual semantic de MCK-006. **Inferível:** densidade standard, filtros, destaque residual como regra UI/UX §21.9. **Não inferível:** colunas FX/doc se API list parcial. **Aceite:** linha=Payment; residual explícito; lote proibido; Create≠Allocate.  
20. FLW-003 entrada alternativa; FLW-004/007  
21. 403; erro+retry  
22. Scroll H/V  
23. OperationalTable a11y  
24. Colunas FX/doc parciais = `GAP_TECNICO`. Validação E9 NECESSARIA.  
25. UI/UX §21.9 · UI/UX §20 (W4)  

**Suficiência visual:** ANALOGA_SUFICIENTE — revalidada 8B (sem AMBIGUIDADE_MATERIAL).  

---

### SCR-011 — Novo pagamento

1. SCR-011 Novo pagamento  
2. Como registro um pagamento sem liquidar ainda?  
3. `/payments/new` (+ query TARGET)  
4. `/payments/new` **sem** query (AS-IS)  
5. Payment  
6. **Owner superfície:** Treasury  
7. **Owners dados:** Treasury; contexto Payable (Billing) se query  
8. `treasury:write`  
9. `treasury:write` · `treasury:register_without_doc`  
10. loading · validação · upload erro · 403 · unsaved TARGET · submit duplicado  
11. Registrar Payment  
12. Override sem doc (TARGET UI)  
13. Override sem comprovante (fluxo `register_without_document`)  
14. supplier · amount · currency · payment_date; **Comprovante:** obrigatório no frontend AS-IS. A ausência é permitida somente pelo fluxo explícito `register_without_document`, condicionado à permissão `treasury:register_without_doc` e à confirmação correspondente.  
15. external_reference; query AP TARGET (`GAP_TECNICO` G02 no AS-IS)  
16. Create **não** altera saldo Payable  
17. PageHeader · Input · MoneyInput · DateInput · File · Button · Notice  
18. Form multipart (MCK-005)  
19. **DIRETA — MCK-005** T0 (+ AUX T1 sucesso)  
20. FLW-003  
21. G02 ausente → banner preencher manual; 403  
22. Form UI/UX §26.8  
23. Labels; unsaved TARGET  
24. **G02** = `GAP_TECNICO`. Validação E9 NECESSARIA. Aceite: Payment criado; Payable intacto; Create≠Allocate.  
25. UI/UX §21.10 · UI/UX §23.3 · MCK-005  

**Suficiência visual:** DIRETA  

---

### SCR-012 — Pagamento e alocações

1. SCR-012 Pagamento e alocações  
2. O que está registrado vs o que será alocado?  
3. `/payments/:paymentId`  
4. Idem  
5. Payment + Allocations + eligible  
6. **Owner superfície:** Treasury  
7. **Owners dados:** Treasury; Payable (Billing) via allocation  
8. `treasury:read`  
9. `treasury:read` · `treasury:allocate` · `treasury:cancel`; painéis FX por ação — ver ficha SCR-009  
10. loading · 403 · 409 · confirmação · docs/audit  
11. Confirmar alocação (batch)  
12. Preview impacto TARGET; FX/docs  
13. Cancel Payment (`treasury:cancel`)  
14. Seleção eligible · valor ≤ residual e ≤ balance · versions · idempotency_key  
15. FX panels  
16. Sem allocation = sem redução; residual sempre visível  
17. PageHeader · OperationalTable · MoneyDisplay · Button · ConfirmationModal · Notice · AuditDocumentsBlock  
18. Detail + allocate (MCK-006 T2)  
19. **DIRETA — MCK-006** T2 (+ AUX T3)  
20. FLW-004  
21. Excesso; inelegível; 409; batch fail → nada aplicado  
22. Full page  
23. Confirmação; focus trap modal `DEFERRED_RUNTIME`  
24. Preview TARGET. Aceite: saldo só pós-allocate; Create≠Allocate.  
25. UI/UX §21.11 · UI/UX §23.4 · MCK-006 · Sistema §6.3  

**Suficiência visual:** DIRETA  

---

## 3. Matriz SCR × rota × capacidade

| SCR | Rota | AS-IS | TARGET | Owner superfície | Owner domínio/dados | Permissão (doc) | Contrato/RM | Gap | Validação E9 | Evidência |
|---|---|---|---|---|---|---|---|---|---|---|
| 001 | `/login` | sim | +`?next=` | identity | Identity | autenticação (sem RBAC shell) | Session | next | NECESSARIA | UI/UX §21.1 |
| 002 | chrome | Ordens/Fin | Compras/Fin | foundation FE | — | por item de nav — ver UI/UX §20.2 | Nav | tema/nav | NECESSARIA | UI/UX §20 |
| 003 | `/orders` | sim | +enrich | Orders | Orders | `orders:read` · `orders:write` | Order list | enrich | NECESSARIA | UI/UX §21.2 · MCK-001 |
| 004 | `/orders/new` | sim | unsaved | Orders | Orders | `orders:write` | Order create | unsaved | NECESSARIA | UI/UX §21.3 |
| 005 | `/orders/:id` | summary/fallback | idem+a11y | Reporting | Orders/Billing/Treasury | `reporting:read` (+ fallback `orders:read`) | order_cockpit | docs deep link | NECESSARIA | UI/UX §21.4 · MCK-002 |
| 006 | `/invoices` | sim (grupo Fin) | Compras+cols | Billing | Billing | `billing:read` | Invoice list | supplier/payable_count | NECESSARIA | UI/UX §21.5 |
| 007 | `/invoices/:id` | sim | preview UX | Billing | Billing | por ação — ver ficha SCR-007 | Invoice | — | NECESSARIA | UI/UX §21.6 · MCK-003 |
| 008 | `/payables` | queue/fallback | +G02 query | Reporting | Billing (+FX) | por ação — ver ficha SCR-008 | ap_queue | G02 L-005 | NECESSARIA | UI/UX §21.7 · MCK-004 |
| 009 | `/payables/:id/fx` | sim | nomenclatura | Treasury | Treasury | por ação — ver ficha SCR-009 | fx-view | hub 028 | NECESSARIA | UI/UX §21.8 · MCK-007 |
| 010 | `/payments` | sim | UI sort/pag | Treasury | Treasury | `treasury:read` · `treasury:write` | Payment list | cols parciais | NECESSARIA | UI/UX §21.9 |
| 011 | `/payments/new` | sem query | +query G02 | Treasury | Treasury | `treasury:write` · `treasury:register_without_doc` | Payment create | G02 | NECESSARIA | UI/UX §21.10 · MCK-005 |
| 012 | `/payments/:id` | allocate API | preview UX | Treasury | Treasury+Billing | por ação — ver ficha SCR-012 | Payment+Alloc | — | NECESSARIA | UI/UX §21.11 · MCK-006 |

SCR-028 hub `/fx`: **não** é ficha Horizon A; `FORA_HORIZON_A` + `GAP_TECNICO`.

---

## 4. Matriz FLW-001…007

| FLW | Origem | Destino | Contexto | Ação | Confirmação | Efeito domínio | Atualização observável | Retorno | 401 | 403 | 404 | 409 | Erro recup. | Concorrência/idem | Evidência | Aceite futuro |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 001 | Cockpit/Order invoices panel | Invoice DRAFT | order_id | POST create invoice | — | Cria Invoice DRAFT; **não** Payable; Order 1:N | Lista invoices Order; Detail DRAFT | Order/Faturas | login | `billing:write` | Order | nº duplicado | msg inline | create não idempotente por nº | UI/UX §23.1 | create≠issue; Billing owner |
| 002 | Invoice DRAFT | ISSUED + N Payables | terms/blockers | Issue UoW | modal preview TARGET | **Cria Payables**; saldo Σ | Status ISSUED; payables | permanece Detail | login | `billing:issue` / `billing:issue_without_doc` | Invoice | version | rollback DRAFT | ensure payables | UI/UX §23.2 | Payable só pós-issue |
| 003 | AP/drawer | Payment Detail | query TARGET | Create Payment | — | Payment REGISTERED; **Payable intacto** | Payment+residual; AP inalterado | Payment; atalho AP | login | `treasury:write` / `treasury:register_without_doc` | payable stale | — | banner G02 | create ≠ liquidar | UI/UX §23.3 | Create≠Allocate |
| 004 | Payment Detail | Allocations | eligible+valores | POST allocations batch | preview TARGET | **Allocation reduz Payable** | residual↓; Payable status | permanece Payment | login | `treasury:allocate` | — | version | nada aplicado | idempotency_key; all-or-nothing | UI/UX §23.4 | sem alloc = sem redução |
| 005 | AP/Cockpit | FX workspace | payable_id | plan/quote/exec/rebind | CORRECTION/rebind | Artefatos FX; **não** reduz Payable | painéis FX | AP | login | por ação — ver SCR-009 | payable | supersede conflicts | stale/error quote | supersedes_id | UI/UX §23.5 | FX≠liquidação |
| 006 | Cockpit | SCR donas | ids | deep link | — | **Nenhum** (RO) | navega dona | cockpit | login | 403 empty | — | — | — | — | UI/UX §23.6 | Cockpit não muta |
| 007 | Ficha | Fila origem | query/linha/scroll TARGET | voltar | — | nenhum | restaura contexto TARGET | fila | `?next=` TARGET | — | — | — | fallback **sem inventar filtro** | — | UI/UX §23.7 | preservação / fallback explícito |

**Preservados:** emissão cria Payables; Payment não reduz; Allocation reduz; FX não liquida; Cockpit só encaminha; retorno TARGET preserva contexto; fallback não inventa filtro/seleção.

---

## 5. Design System × telas (rastreio enxuto)

| Token/componente | Tela(s) | Variante | Densidade | Composição | Estado | Proveniência | A11y | DEFERRED_RUNTIME | Norma |
|---|---|---|---|---|---|---|---|---|---|
| AppShell/Sidebar | 002–012 | navy 220 | — | chrome | sticky | DERIVED | landmarks | skip/teclado | UI/UX §27.1 |
| PageHeader | 003–012 | +actions | — | H1 22 | — | DERIVED | heading | — | UI/UX §27.1 |
| Button size.md/lg | várias | ghost/primary | vh 32/36 | ações | busy/disabled | NORMALIZED | focus | hover real | UI/UX §27.2 |
| FilterChip | 003,008,010 | on/off | vh 28 hit≥32 | filtros | — | TARGET | hit area | — | UI/UX §27.2 |
| OperationalTable | 003,006,008,010 | — | std 40 / fin 44 | filas | empty/error | NORMALIZED | sticky col | virtualização | UI/UX §27.3 |
| StatusBadge | várias | 5 semânticas | vh 20 | status | — | DERIVED | não só cor | — | UI/UX §27.3 |
| Money/RateDisplay | várias | — | — | valores | — / stale | DERIVED | tabular | — | UI/UX §27.3 |
| KpiStrip | 005,008,012 | — | — | KPIs | omit fallback | DERIVED | — | — | UI/UX §27.3 |
| Input/Select | 004,007,011 | form 32 | — | forms | error/focus | NORMALIZED | label | — | UI/UX §27.4 |
| DetailDrawer | 008 | width 460 | — | preview | — | DERIVED | Escape | focus trap | UI/UX §27.6 |
| ConfirmationModal | 007,012,AUX | — | — | confirm | — | DERIVED | — | trap | UI/UX §27.6 |
| AuditDocumentsBlock | 002,003,004,007 | page/drawer | — | docs/audit | empty | DERIVED | list | deep link páginas | UI/UX §27.7 |
| detailDrawer.width | 008 | 460 | — | só DetailDrawer | — | DERIVED | — | — | UI/UX §26.5 |
| type.size.id | filas | 12 | — | IDs | — | NORMALIZED | — | — | UI/UX §26.4 |
| radius.chip | chips | 14 | — | FilterChip | — | NORMALIZED | — | — | UI/UX §26.5 |
| Tema light vs dark AS-IS | global | — | — | — | — | TARGET vs AS_IS | — | — | UI/UX §27.10 |

---

## 6. Conteúdo e nomenclatura (regras comuns)

Fonte: UI/UX §26.9 · UI/UX §25.6 · glossário Sistema.

| Tema | Regra |
|---|---|
| Idioma UI | Português |
| Pedido / Fatura / Obrigação / Pagamento / Alocação | Vocabulário oficial |
| Câmbio | **Câmbio da obrigação** (não “Fila FX” ao usuário) |
| Contas a pagar | Por extenso (não “Fila AP” ao usuário) |
| Moeda | Sempre explícita |
| Datas | `DD/MM/AAAA`; horário com timezone |
| Ausência | `—`; **nunca** zero inventado |
| Vazio ≠ zero | Empty state ≠ valor 0 |
| Códigos domínio | Visíveis; IDs **sem** tradução |
| Abreviações | Evitar; labels acessíveis por extenso |
| Personas ≠ roles | Personas orientam; perms = seed documentado |

---

## 7. Índice de assets × SCR

Base relativa: `docs/v2/blueprint UIUX/mockups/mck-v1.1/`.  
PDF consolidado: `docs/v2/blueprint UIUX/mockups/mck-v1.1/review/MCK-v1.1-visual-review.pdf` (8 páginas).

| SCR | MCK | SVG | PDF pág | PNG 1440 | Smoke 1366 | Momento | AUX | Limitação evidência |
|---|---|---|---|---|---|---|---|---|
| 001 | — | — | — | — | — | — | — | Sem artboard; wire UI/UX §21.1 + shell MCK |
| 002 | 001–007 shell | (shell em todos `source/MCK-00x-*.svg`) | 1–7 | (shell em todos `review/MCK-v1.1-1440/MCK-00x-*-1440.png`) | (shell em todos `review/smoke-1366/MCK-00x-*-1366x768.png`) | — | — | Shell transversal |
| 003 | 001 | `source/MCK-001-orders.svg` | 1 | `review/MCK-v1.1-1440/MCK-001-orders-1440.png` | `review/smoke-1366/MCK-001-orders-above-fold-1366x768.png` | T0 | — | Enrichment não mockado como dado real |
| 004 | — | — | — | — | — | — | — | Análogo MCK-003 + MCK-005 + shell MCK-001 |
| 005 | 002 | `source/MCK-002-order-cockpit.svg` | 2 | `review/MCK-v1.1-1440/MCK-002-order-cockpit-1440.png` | `review/smoke-1366/MCK-002-order-cockpit-above-fold-1366x768.png` | T0 | — | RO |
| 006 | — | — | — | — | — | — | — | Análogo MCK-001 + UI/UX §20 W2 |
| 007 | 003 | `source/MCK-003-invoice.svg` | 3 | `review/MCK-v1.1-1440/MCK-003-invoice-1440.png` | `review/smoke-1366/MCK-003-invoice-above-fold-1366x768.png` | T0 | AUX FLW-002 | Rascunho |
| 008 | 004 | `source/MCK-004-ap.svg` | 4 | `review/MCK-v1.1-1440/MCK-004-ap-1440.png` | `review/smoke-1366/MCK-004-ap-above-fold-1366x768.png` | T0 | — | G02 visual TARGET no mock ≠ wiring |
| 009 | 007 | `source/MCK-007-fx.svg` | 7 | `review/MCK-v1.1-1440/MCK-007-fx-1440.png` | `review/smoke-1366/MCK-007-fx-above-fold-1366x768.png` | T0 | — | Sem hub 028 |
| 010 | — | — | — | — | — | — | — | Análogo MCK-001 + UI/UX §20 W4 |
| 011 | 005 | `source/MCK-005-payment-new.svg` | 5 | `review/MCK-v1.1-1440/MCK-005-payment-new-1440.png` | `review/smoke-1366/MCK-005-payment-new-above-fold-1366x768.png` | T0 | AUX T1 | |
| 012 | 006 | `source/MCK-006-payment-detail.svg` | 6 | `review/MCK-v1.1-1440/MCK-006-payment-detail-1440.png` | `review/smoke-1366/MCK-006-payment-detail-above-fold-1366x768.png` | T2 | AUX T3 | Prévia ≠ runtime |
| — | AUX-01 | `source/MCK-AUX-01-states.svg` | 8 | `review/MCK-v1.1-1440/MCK-AUX-01-states-1440.png` | `review/smoke-1366/MCK-AUX-01-states-above-fold-1366x768.png` | T1/T3 | estados/erros | Consultivo |

Todos os paths acima foram verificados como existentes sob `mockups/mck-v1.1/` na consolidação 8B.

---

## 8. Registro de gaps e decisões abertas

| Gap | Origem | Classificação | Impacto | Dependência | Decisão necessária | Destino | Validação Etapa 9 | Evidência |
|---|---|---|---|---|---|---|---|---|
| G02 AP→Novo pagamento query | UX-1 / UI/UX §21.7 / §21.10 / FLW-003 | `GAP_TECNICO` | Contexto lost | FE query + CTA AP | Wiring | Etapa 9 | NECESSARIA | UI/UX §23.3 · UI/UX §25.5 |
| Query/linha/scroll retorno | UI/UX §21.0 · FLW-007 | `GAP_TECNICO` / `TARGET` | Contexto fila | FE router state | Completar preservação | Etapa 9 | NECESSARIA | UI/UX §23.7 |
| Login `?next=` | UI/UX §21.1 | `GAP_TECNICO` | Deep link pós-login | Auth redirect | Implementar next seguro | Etapa 9 | NECESSARIA | UI/UX §21.1 |
| Docs/Audit deep link | UI/UX FLW-006 · §25.5 | `GAP_TECNICO` | Sem página dedicada | Rotas docs/audit | Spec páginas | Etapa 9 | NECESSARIA | UI/UX §23.6 |
| Enrichment fila Pedidos | UI/UX §21.2 · §25.5 | `GAP_TECNICO` | Colunas "—" | Read model | Extensão API/RM | Etapa 9 | NECESSARIA | UI/UX §21.2 |
| supplier_name / payable_count Faturas | UI/UX §21.5 | `GAP_TECNICO` | Colunas incompletas | InvoiceListItem | Extensão contrato | Etapa 9 | NECESSARIA | UI/UX §21.5 |
| SCR-028 hub Câmbio | UI/UX §4 · §20 · §25.5 | `GAP_TECNICO` + `FORA_HORIZON_A` | Nav morta se fingir | Rota+RM `/fx` | ADR/produto | Etapa 9 / ADR | NECESSARIA | UI/UX §20.2 |
| L-005 reporting:read | Sistema / UI/UX §21.12 | `DECISAO_ABERTA` | Admin-only vs alvo | Matriz papéis | Validação Epic | Negócio+Etapa 9 | NECESSARIA | Sistema (L-005) |
| Comprador × Treasury write/allocate | UI/UX §21.12 · Roadmap | `DECISAO_ABERTA` | Perm seed vs Blueprint básico | RBAC | Decisão produto | Negócio | NECESSARIA | UI/UX §21.12 |
| DEC-ACCONTO-INVOICE | Sistema §5.7 | `DECISAO_ABERTA` | Tipo não operacional | Exemplar/negócio | Tipar ou não | Negócio | NECESSARIA | Sistema §5.7 |
| Teclado / focus trap / restore / SR | UI/UX §26.7 · §27 | `DEFERRED_RUNTIME` | A11y runtime | FE | Implementar/medir | Etapa 9 | NECESSARIA | UI/UX §26.7 |
| Virtualização / perf volume | E6A E6-017 · UI/UX §27.3 | `DEFERRED_RUNTIME` / `GAP_TECNICO` | Filas grandes | FE | Estratégia perf | Etapa 9 | NECESSARIA | UI/UX §25.5 · E6A E6-017 |
| Tema AS-IS dark → TARGET light | UI/UX §27.10 | `GAP_TECNICO` | Visual global | FE tokens | Troca tema | Etapa 9 | NECESSARIA | UI/UX §27.10 |
| Componentes AS-IS vs DS | UI/UX §27.10 | `GAP_TECNICO` | Paridade visual | FE | Mapear componentes | Etapa 9 | NECESSARIA | UI/UX §27.9 / §27.10 |
| D-DOC-01 legenda v3.9 | Legenda MCK | documental (ACEITA) | Confusão versão mitigada | — | Nenhuma alteração MCK | Encerrado 8B | NAO_NECESSARIA | Handoff §1.1 |

**Nenhum gap técnico ou decisão aberta foi resolvido nesta etapa** — apenas isolados e rastreados.

---

## 9. Horizon B–D — limites

| Tema | Tratamento |
|---|---|
| Capacidades conceituais | Existem no mapa UI/UX §4 (SCR-013…036) e Sistema módulos futuros |
| Reuso Horizon A | Shell, tabelas, badges, money, estados UI/UX §21.0, padrões DS |
| Fora da navegação A | Workbench, Produtos, Importação, Abastecimento, Custos, Admin rico, hub SCR-028 |
| Nova fatia | Qualquer SCR B–D exige fatia de produto + mock/spec próprios |
| Nav morta | **Proibido** renderizar item sem rota/RM (regra UI/UX §14 / §20) |
| Classificação | `FORA_HORIZON_A` |

**Não** há fichas SCR-013…036 neste handoff.

---

## 10. Definition of Ready (Etapa 9) — fechado na 8B

| Gate | Status 8B |
|---|---|
| Estado documental sincronizado (MCK 1.1 · UI/UX 3.10 · Sistema 0.2.8 · Roadmap 8B) | `ATENDIDO` |
| 12 fichas completas (25 campos) | `ATENDIDO` |
| Sete FLWs rastreados | `ATENDIDO` |
| Ref visual direta ou análoga por SCR | `ATENDIDO` — 001/004/006/010 = ANALOGA_SUFICIENTE; sem AMBIGUIDADE_MATERIAL |
| Tokens/componentes relacionados | `ATENDIDO` (matriz §5) |
| Gaps/DECs isolados | `ATENDIDO` (§8) — **não resolvidos**; não impedem investigação |
| Contratos não inventados | `ATENDIDO` |
| B–D não como runtime | `ATENDIDO` (§9) |
| Critérios de aceite verificáveis | `ATENDIDO` |
| Autoridades/versões explícitas | `ATENDIDO` |
| Sem contradição Sistema cardinalidades | `ATENDIDO` |
| Etapa 9 capaz de investigar sem redesenhar | `ATENDIDO` |
| **DoR fechado** | `ATENDIDO` |

O DoR libera o **planejamento** da Etapa 9; **não** autoriza execução automática de implementação.

**Exceções AMBIGUIDADE_MATERIAL:** nenhuma.

---

## 11. Checkpoint e próxima ação

```text
Etapa 8 = DONE
Handoff = v1.0 CONSOLIDADO
E8-A = APROVADO COM AJUSTES (ajustes CONCLUÍDOS)
E8-B = APROVADO
Etapa 9 = NÃO INICIADA
Inc-6 = TODO (trilha técnica separada)
```

**Próxima etapa lógica:** Etapa 9 — investigação e planejamento técnico da implementação. Não executar implementação nesta ação.
