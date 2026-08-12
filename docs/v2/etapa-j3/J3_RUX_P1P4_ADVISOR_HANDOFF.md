# J3-RUX — P1–P4 Decision Package — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | Planning P1–P4 (DEC-RUX-ORDERITEM-NULL + reescopo 3A + desenho 2R-b + limpezas) |
| Status | **DONE** (pacote documental — **sem** implementação) |
| Data | 2026-08-06 |
| Árvore | alembic **019**; Q3=(B); C1–C5 **ACEITO** |
| Autorização | RUX-2R-b / 3A / 3B / J#6 = **NÃO** |

**Escolha final P1 = decisão de negócio do Ricardo.** Este handoff entrega impacto técnico por opção — não uma preferência disfarçada.

---

## WIP na árvore — NÃO desta fatia (regra C5)

1. Modelo B `begin_nested` + PARTIAL em `commit_commands.execute_commit`
2. `staging_commands.reextract_document` (rota 501)
3. Migration 020 em `_wip_isolated_rux3a_rux2rb/` (fora da chain)
4. Docs DRAFT #4/#5 sem `order_number` (lixo; fora do 589)

---

## P1 — DEC-RUX-ORDERITEM-NULL (material de decisão)

### Fatos

| Fato | Evidência |
|---|---|
| `OrderItem.product_id` **NOT NULL** | [`orders/models.py`](../../v2/app/orders/models.py) + migration `002` |
| Order DRAFT **só cabeçalho** é representável | `create_order` sem itens; **sem** constraint ≥1 item; Fattura Policy **C1** já cria DRAFT vazio |
| Confirm exige ≥1 item | `confirm_order` + UI create |
| Commit Ordine bloqueia linhas sem Product | `preview_commit` — 589 **não** gera Order com as 2 linhas I.V.* |

### Quem lê `OrderItem.product_id` (produção)

| Módulo | Lê? | Se nulo |
|---|---|---|
| Orders API (`_order_response`) | Sim (1) | OpenAPI `number` quebra contrato |
| Billing (`create_invoice` / `replace_items`) | Sim (2 loops) | Copia para `InvoiceItem.product_id` (**NOT NULL**) — **quebra** |
| Logistics / Customs / Inventory / Reporting | Não | 0; usam `order_item_id` ou snapshots |
| Pedidos UI detail | Não | Create exige product resolvido |

**Total: 3 funções** leem `.product_id`; nenhuma tem null-check (seguro só pelo NOT NULL no insert).

### Precedente de linha sem entidade resolvida

- **Sim:** `CustomsDoganaleLine.product_id`, `NationalizationItem.product_id` (nullable).
- **Não** na cadeia Order → Invoice → Inventory.

### Reconciliação Fattura ↔ compromisso Ordine

**Inexistente** linha-a-linha (descrição/qty/SKU).

- Match Order: `supplier_id` + `external_ref` (cabeçalho).
- Policy **A**: Invoice copia todos `order.items` (ignora IR Fattura para composição).
- Policy **C2**: itens novos do IR com `product_id_catalog` — sem casar Order prévio.
- Casar `14.600 PZ "racchette 2027 GRAFICATE"` ↔ EANs Fattura = **estrutura nova**, qualquer opção que separe compromisso de Product.

### Alternativas — impacto (Ricardo escolhe)

#### (1) `product_id` nullable + snapshots de compromisso no OrderItem

| | |
|---|---|
| **Muda** | Migration Orders; `add_item` sem resolve; API optional; guards billing |
| **Custo** | Médio–alto (Orders+Billing+i3+UI); InvoiceItem ainda NOT NULL → não fatura compromisso cru |
| **Risco** | Contamina agregado Order; confirm/invoice precisam regra “só com product”; residual logística ambíguo |
| **Catalog Ordine** | Só supplier |

#### (2) Order DRAFT só cabeçalho até a Fattura

| | |
|---|---|
| **Muda** | Commit Ordine: order+link **sem** `add_item`; preview relaxa product em I.V.* |
| **Custo** | Baixo–médio no schema (header-only já existe); médio na jornada (Order vazio; Fattura A exige itens) |
| **Risco** | Order pouco útil; reconciliação ainda nova; órfãos/duplicata C1; confirm bloqueado |
| **Catalog Ordine** | Só supplier |

#### (3) Compromisso no staging IR até a Fattura (sem OrderItem)

| | |
|---|---|
| **Muda** | Ordine = supplier + promote (± Order header); linhas I.V. nunca viram OrderItem |
| **Custo** | Baixo schema; **alto** UX (pedido na ingestão) |
| **Risco** | Duas verdades IR/Order; Policy A não herda 14.600 PZ; matching descrição frágil |
| **Catalog Ordine** | Só supplier |

#### (4) Order header + vínculo IR + reconciliação na Fattura (proposta)

| | |
|---|---|
| **Muda** | Como (2)/(3) no Ordine; **nova** allocation Fattura (EAN/Product → qty vs linha compromisso) |
| **Custo** | Alto (produto+modelo+UI Fattura); quase zero em nullable OrderItem |
| **Risco** | Escopo grande; preserva invariante OrderItem↔Product; alinhado Q3=(B) |
| **Catalog Ordine** | Só supplier; Products na Fattura (EAN→`Product.sku` já existe) |

### Leitura técnica (não decisão de negócio)

- Bloqueio RUX-3B é **real** (NOT NULL).
- Billing exige Product — (1) sozinho não fecha Policy A.
- Sem reconciliação linha, (2)/(3)/(4) empurram desenho para Fattura.
- **Ricardo decide (1)–(4).**

---

## P2 — Reescopo RUX-3A pós-Q3=(B)

| Peça 020 | Sobrevive Q3=B? | Ordine |
|---|---|---|
| `tax_id` | Ortogonal | Melhora PI; **não bloqueia** (match atual name/ILIKE) |
| `country_code` | Já **019** | OK |
| `product_sku_seq` | Não para I.V.* | Só ao criar Product real (Fattura/operador) |
| refs / `code_kind` / fingerprint | Não para I.V.* | EAN Fattura = `Product.sku`; refs = futuro, não mínimo |
| Reaplicar 020 | **Proibido** | Premissa morta |

### Migration mínima Catalog para Ordine

| Se P1 = | Mínimo |
|---|---|
| (2), (3), (4) | **Nenhuma**; opcional depois **tax_id-only** (estreita, sem refs/seq) |
| (1) | Migration **Orders** (nullable + compromisso) — **não** 020; Catalog refs/seq ainda desnecessários |

**Sobrou pouco:** no limite **zero** Catalog; no máximo tax_id ortogonal. Refs/seq fora do Ordine.

---

## P3 — Desenho mínimo RUX-2R-b (só desenho; NÃO autorizado)

### Defeito

`execute_commit` → `begin_nested` por op → early `PARTIAL` → rota **sempre** `uow.commit()` → writes + ledger PARTIAL persistem. Contrato ambíguo antes de RUX-3B.

### Fatia mínima (transação + ledger)

**Fora:** reextract UI, readiness, PendencyList, Catalog, Orders nullable.

**Dentro (default “confiável”):**

1. **All-or-nothing:** remover `begin_nested`; falha → `FAILED` + route **rollback**; `uow.commit()` **somente** se `SUCCEEDED`.
2. **Eliminar PARTIAL** do caminho Ordine nesta fatia (salvo decisão explícita de “PARTIAL honesto”).
3. Ledger na mesma txn (retry limpo) — default simples.
4. Testes all-or-nothing (substituir Modelo B tx isolado).
5. Alinhar rota Fattura ao mesmo gate se commit cego.

**reextract:** no mesmo PR — (a) manter 501 declarado WIP, ou (b) extrair/remover com Modelo B. Default desenho: isolar junto.

---

## P4 — Limpezas (listadas; não executadas nesta Planning)

| Item | Estado real | Próxima fatia exec |
|---|---|---|
| OpenAPI | Catalog `Supplier*` **já limpo**; `tax_id` restante = **Payee** (legítimo). C1C5 §C5.3 estava desatualizado — **corrigido abaixo** | Regenerar só se API mudar |
| Fila #4/#5 vs #7 | **Sem contradição:** #7 = único DRAFT bom **Ordine 589**; #4/#5 = DRAFT lixo sem `order_number` | Redação clarificada; opcional REJECT #4/#5 |
| reextract vivo + 501 | Impl. viva; rota gated | Decisão junto RUX-2R-b |

---

## Próxima etapa lógica

1. **Ricardo decide P1** (1)/(2)/(3)/(4).
2. Autorizar **RUX-2R-b (P3)** antes de qualquer RUX-3B.
3. RUX-3A Catalog só se tax_id-only ou Fattura pedir refs — **nunca** 020.

## PROIBIDO agora

Implementar; migrations; aplicar 020; iniciar RUX-2R-b/3A/3B; J#6.

```text
DOC_DELTA
- Updated: docs/v2/etapa-j3/J3_RUX_P1P4_ADVISOR_HANDOFF.md; J3_EXECUTION_PLAN.md; J3_RUX_C1C5_ADVISOR_HANDOFF.md (P4 redação); ROADMAP_V2_EPIC.md; plan mestre j3-rux
- Evidence: este handoff (pacote P1–P4)
- Roadmap status: 0.5.81 — P1–P4 Planning DONE; aguarda decisão Ricardo P1
- Next TODO: Ricardo decide DEC-RUX-ORDERITEM-NULL; depois auth RUX-2R-b
- Return to advisor: docs/v2/etapa-j3/J3_RUX_P1P4_ADVISOR_HANDOFF.md
```
