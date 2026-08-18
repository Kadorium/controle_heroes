# Elo 8 — Plano mestre

Espelho de decisão: [`E8_ADVISOR_HANDOFF.md`](E8_ADVISOR_HANDOFF.md).  
**Este é o mestre da fase.** Não criar `.plan` concorrente. Não reabrir E8-0…E8-6.

| Campo | Valor |
|---|---|
| Campanha | Elo 8 — nacionalizado → estoque por produto |
| Status | **ENCERRADA / DONE** — aceite advisor 2026-08-17. Não relançar. Não hardening. |
| Roadmap | **0.5.123** — elo 8 LIGADO (produto no catálogo); cadeia 8/10; 202 documental → estoque; Aduana 2/3 |
| Blueprint | **0.2.24** — PATH / BIND / COVERAGE / STUBS em §5.12 / §7.11 |
| Alembic | **025** — sem 026 |
| Lane | `:8082` / `epic_v2_test` / cookie `epic_v2_test_session` |
| Operação | `:8081` / `epic_v2` — inspeção; 589 e TESTE-CICLO-001 intocados |
| Próxima ação (B.1) | Pagar numerário no tesouro — **não** é Elo 8 |

---

## Coerência com o plano anterior (Q1–Q7)

O Cursor plan e o bloco de autorização no handoff **vinculam** este mestre. Divergências do rascunho inicial (C na rota; barras antes do walk; select com BONDED/RECLASS; `cleared_not_received` como residual do processo) estão **refutadas**. Não reabrir.

| ID | Achado autorizado | No mestre / na execução |
|---|---|---|
| **Q1** | NAT-REVERSE = **B**. C na rota Customs = ciclo (`ALLOWED_DEPS` em todo o pacote). A refutado. | Hide Reverter na UI. API → item **`E8-NAT-REVERSE-API`** (Roadmap B.3). Walk **não** reverteu nacionalização |
| **Q2** | Falha no walk + pytest: corrigir → pytest full → re-bootstrap → re-walk. Máx. 3. Sem skip/only, sem editar OpenAPI gerado, sem preservar massa | Loop usado na campanha (over-receipt deixava DRAFT; double-click sequencial criava dois receipts). Fechado no código; walk PASS |
| **Q3** | `cleared_not_received` = agregado **global** (ex. 6 + 10 = **16**). Rotular escopo; não esconder; ReceiptPanel ignora o campo | Rótulo: «Agregado do produto em todos os processos — não é o residual deste processo.» |
| **Q4** | Sem grupo de produto. Fixture **EAN_DESC**. Pedido na mão = `description = sku`. “Sem ID cru” é nominal se só EAN | Walk mostrou `WASH BAG STARLIGHT - RED` + EAN. Elo 8 **não** altera `OrderCreatePage` |
| **Q5** | Após PASS: LIGADO **só** com produto no catálogo; **J#5-REC** na ressalva; 8/10 só com a condição escrita. Aduana 2/3 | Aplicado em 0.5.121. Ressalva **não** apagada |
| **Q6** | Select congelado **`DOMESTIC_IN`**. Entreposto = backlog datado, não esta campanha | Caso A em B.6 (2026-08-17). BONDED/RECLASS intactos na API/pytest |
| **Q7** | Cabeçalho asset+porta. Atrito na mesma linha. Texto literal. Não consertar no percurso | Tabela W1–W8 abaixo. Atrito **não** vira fatia nova |

**Não misturar** com Elo 7, settlement CUSTOMS_FUNDING, J#6, Dashboard, fechar Order, B0, 3A/020, J#5-REC, E7-ARRIVAL-GATE.

---

## DECs (ratificadas; não relitigar)

- **PATH** — Gate = Caso B (`DOMESTIC_IN`). Select congelado. “Usamos entreposto” **não** alarga E8.
- **BIND** — Candidatos e qty só do residual item-level. 0/1/N visível. Sem auto-confirm. Sem IDs crus.
- **COVERAGE** — Fonte canónica = query item-level. Confirm doméstico exige `nationalization_item_id`; `product_id` da linha = item da liberação. Sem fallback global-por-produto no caminho operador. Multi-processo obrigatório.
- **ARRIVAL** — Não implementar E7-ARRIVAL-GATE; não exigir ARRIVED no receipt.
- **DOC** — Sem PDF novo no receipt.
- **NAT-REVERSE** — **B**. C refutado. Hide UI. Furo API nomeado, não anónimo.
- **STUBS** — Não implementar `in_clearance` / `in_transit` / `future_order`. Não pintar stub como zero.

### Residual recebível (única fonte do ReceiptPanel)

```
NationalizationItem CONFIRMED
  → nationalized_qty
  → received_qty  (DOMESTIC_IN|RECLASS CONFIRMED do MESMO nationalization_item_id)
  → residual_qty
```

Draft / REVERSED não consomem. Não usar `sum_nationalized_qty_by_product` nesta query nem na UI.

Handoff de fecho (já escrito): *Residual recebível do processo é provado pela query item-level; SkuPosition é verificação agregada física (todos os processos), não o residual deste processo.*

---

## Como executar (se a campanha fosse relançada)

Não relançar. Ordem que **foi** seguida e permanece a única ordem válida:

```
E8-0 → E8-1 → E8-2 → E8-3 → E8-4 (pytest full) → re-bootstrap fixture → E8-5 (só UI) → E8-6
```

Pytest `drop_all` em `epic_v2_test`. Walk **depois** do pytest. Fixture **só pré-W1**. Pós-W1: zero POST inventory por script.

Runtime: Vite `dev:test` em `http://localhost:5174` (não `127.0.0.1` — escuta IPv6) → `:8082`. Rebuild **não** importa `SessionLocal` de `database.py` (pode ligar a `epic_v2`). Pacote Python = `v2/` na raiz, não `docs/v2`.

Double-click de prova: dois `click()` no **mesmo** tick (`evaluate`), não dois `await click()` sequenciais.

---

## Fatias — autorizado → feito

### E8-0 Preflight — DONE

Runtime 8082 / `epic_v2_test` / Alembic 025. `epic_v2` intocado. Sem 026. Evidência: [`P0_RUNTIME.md`](P0_RUNTIME.md).

### E8-1 Residual + COVERAGE — DONE

`GET /api/inventory/processes/{id}/receipt-residuals`. Confirm doméstico/reclass exige `nationalization_item_id`; mismatch de produto → 422. Fallback global **fora** do caminho operador. Multi-processo: residuais 6 e 10, `cleared_not_received` = 16. Sem import Inventory em Customs. Diário: NAT-REVERSE = B.

### E8-2 ReceiptPanel — DONE

Tabela só E8-1. Select **só** `DOMESTIC_IN`. Location DOMESTIC. Sem input de ID. Um draft; busy. Hide Reverter se `received_qty > 0`. Fixture `EAN_DESC`. Over-qty **no cliente** (não criar DRAFT residual — lição Q2).

### E8-3 Verificação — DONE

Copy `over_receipt` pt-BR. `balances` na posição SKU. `goods_receipt.*` na auditoria do processo (`customs-section-audit`). Rótulo de escopo em Liberado não recebido. Stubs «Não disponível». Link SKU → `/inventory/sku/:id`.

### E8-4 Pytest — DONE

Pytest **full** verde **antes** da massa. Vitest Elo 8. Drift OK. Passos inventory/nat do e2e J#5 actualizados (sem `page.evaluate(fetch)` de IDs). SC-10 (Caso A) permanece pytest-only.

### E8-5 Walk — DONE / PASS

Mutações Inventory **só UI** após W1. Lista de APIs no handoff. Atrito anotado, **não** corrigido no percurso.

### E8-6 Fecho — DONE

B.2 reescrito com condição catálogo + J#5-REC. Cadeia 8/10. Aduana 2/3. `E8-NAT-REVERSE-API` em B.3. Blueprint PATH/BIND/COVERAGE/STUBS. Caso A datado em B.6.

---

## Walk W1–W8 (resultado)

**Cabeçalho:** Vite `dev:test` **`:5174`** (`localhost`) → `:8082` / `epic_v2_test` / Alembic **025**. Login `admin@epic.com.br`.  
**Fixture pré-W1:** processo `IMP-C053F7E3E212` (`PARTIALLY_CLEARED`); nat CONFIRMED; zero receipts; pedido mock `E8-202-MOCK` (continuação conceitual da família 202; **não** Ordine PDF — DEC-E8-DOC).

| Passo | Vi / Cliquei / Resultado | Canal | Atrito (anotar, não fatia) |
|---|---|---|---|
| W1 | STARLIGHT + `8057628953814` 50/0/50; FIERCE 10/0/10; só `DOMESTIC_IN`; sem `receipt-product-id` | UI | — |
| W2 | Qty 20 STARLIGHT (FIERCE zerado); double-click mesmo tick; `#1 · Entrada doméstica · Confirmado`; residual 30 | **UI** | Extra clique para zerar FIERCE |
| W3 | Δ 20; `Disponível 20`; Liberado não recebido 30 + rótulo agregado; saldo DOMESTIC-MAIN 20; persiste no reload | UI | — |
| W4 | Segundo receipt 30; `Disponível 50`; STARLIGHT sai da tabela | **UI** | Qty proposta não resetou ao residual 30 |
| W5 | Qty 99 no FIERCE; hint + copy over_receipt; sem rascunho | **UI** | Excesso no outro SKU (3814 já residual 0) |
| W6 | FIERCE 10; `#3 Confirmado`; «Nada a receber» | **UI** | — |
| W7 | Reverter liberação oculto («já há estoque recebido»); estorno do receipt mais novo; re-receber `#4` | **UI** | — |
| W8 | Auditoria: Recebimento criado / linhas / confirmado / estornado | **UI** | Quem = `"1"` |

Screenshots: [`screenshots/`](screenshots/). Log: [`logs/e8-walk-log.json`](logs/e8-walk-log.json).

**Não no walk (e não nesta campanha):** pagar numerário; Caso A; reverse de nacionalização; location nova; POST inventory fora da UI.

---

## Fora do Elo 8 (não executar como E8)

| Item | Onde vive | Não fazer agora |
|---|---|---|
| Settlement CUSTOMS_FUNDING | Roadmap B.1 | Próxima campanha — tesouro |
| J#5-REC | B.2 ressalva | Compromisso sem Product |
| `E8-NAT-REVERSE-API` | B.3 | Guard sem ciclo `customs` → `inventory` |
| Caso A / entreposto UI | B.6 2026-08-17 | Não descongelar o select |
| Qty proposta que não reseta; actor `"1"` | Roadmap B.6 2026-08-17 | **Não** polir nesta campanha |
| E7-ARRIVAL-GATE | B.6 | Não exigir ARRIVED no receipt |

---

## Paragem (só se alguém relançasse)

Migration inesperada; tentar ciclo `customs` → `inventory`; exigir CUSTOMS_FUNDING; reabrir Elo 7; três falhas no mesmo ponto após Q2.

Não usar BLOCKED para aprovação comum de fatia. Sem aceite intermédio — a campanha **já fechou**.
