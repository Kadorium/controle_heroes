# J3-RUX — V1–V3 Decision Package — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | Planning V1–V3 (confirm→invoice + opção (1) apertada + P3 FS/Fattura) |
| Status | **DONE** (pacote documental — **sem** implementação) |
| Data | 2026-08-06 |
| Árvore | alembic **019**; P1–P4 **ACEITO**; Q3=(B) |
| Autorização | RUX-2R-b / 3A / 3B / J#6 = **NÃO** |

---

## WIP na árvore — NÃO desta fatia (regra C5)

1. Modelo B `begin_nested` + PARTIAL em `execute_commit`
2. `staging_commands.reextract_document` (rota 501)
3. Migration 020 em `_wip_isolated_rux3a_rux2rb/`
4. Nullable `OrderItem.product_id` — **ainda não** no schema (só desenho V2)

---

## V1 — Encadeamento confirm → invoice (evidência)

### 1. `confirm_order` exige ≥1 item?

**Sim — validação de domínio, não constraint DB.**

Em [`orders/commands.py`](../../v2/app/orders/commands.py) ~184–191:

```python
if not order.items:
    raise OrderValidationError("Ordem sem itens não pode ser confirmada")
```

Header-only DRAFT **persiste**; só a transição para CONFIRMED é bloqueada.

### 2. Invoice exige Order CONFIRMED?

**Sim.** Em [`billing/commands.py`](../../v2/app/billing/commands.py) ~90–91:

```python
if order.status != "CONFIRMED":
    raise InvoiceValidationError("Só é possível faturar ordem CONFIRMED")
```

Também exige ≥1 item após filtro. Policy **A** Fattura só com Order CONFIRMED.

### 3. Header-only → nunca confirma → nunca fatura?

**Como estado terminal: sim.**

| Afirmação | Veredito |
|---|---|
| Order só cabeçalho não confirma enquanto vazia | **Confirmado** |
| Sem CONFIRMED não fatura | **Confirmado** |
| Elimina (2)/(3)/(4) **por construção absoluta** | **Refutado** — sobrevivem se houver passo que **adicione itens com Product** antes do confirm |
| Elimina (2)/(3)/(4) como jornada Ordine→Invoice **fechada sem** popular itens depois | **Confirmado** — Policy A nunca engata em header-only |

**Para Ricardo:** risco “confirm bloqueado” do P1 é **factual** para Order vazia como fim de linha. Opções (2)/(3)/(4) **morrem** sem desenho explícito de popular itens depois.

### 4. Policy C1 — Orders vazias

- C1 cria Order DRAFT **sem** itens (`PENDING_CONFIRM`); não confirma até haver itens.
- C2 popula itens antes de `confirm_order` (comentário explícito no código).
- **`epic_v2` (2026-08-06):** `empty_draft_count = 0`. Orders: 1 DRAFT (com itens), 15 CONFIRMED, 4 CANCELLED. **Nenhuma vazia presa hoje**; código C1 ainda **pode** criá-las.

---

## V2 — Opção (1) apertada (desenho; não implementar)

Direção: `product_id` nullable só em compromisso; snapshots do documento; InvoiceItem **NOT NULL**; sem reconciliação linha nesta fatia.

### Migration Orders mínima

- `order_items.product_id` NULL permitido.
- Compromisso: `external_code` (nullable); `product_id IS NULL` = compromisso (ou `line_kind`).
- Snapshots existentes: sku/description/qty/unit_price do IR.
- **Sem** Catalog / 020.

### Guards (3 call sites)

| Site | Comportamento |
|---|---|
| `_order_response` | `product_id: int \| null` |
| `create_invoice` | Só linhas com `product_id`; se zero → erro *nenhuma linha faturável* |
| `replace_items` | Idem |

### Policy A com só compromisso

→ 0 linhas faturáveis → **falha explícita**. Não inventar Product.

### `confirm_order` — desenho adotado: **variante A**

| Variante | Efeito |
|---|---|
| **A (adotada)** | Confirma se ≥1 item (mesmo 100% compromisso) |
| B | Bloqueia se alguma linha sem Product — (1) pouco ajuda 589 |
| C | A + aviso/audit |

Motivo: Q3=(B); fronteira de fatura em InvoiceItem NOT NULL; sem exigir reconciliação agora. **Ricardo pode trocar para B.**

### OpenAPI / client

Regenerar: `product_id` nullable; Create pode omitir product em compromisso.

### Direção errada?

**Não refutada.** Caveat esperado: Policy A não fatura 589 só-compromisso até existir Product.

---

## V3 — P3 corrigido (filesystem + Fattura)

### P3-a — Filesystem

`store_document` escreve disco **antes** do flush; rollback DB **não** apaga arquivo.

**Desenho:** write em **temp** → `uow.commit()` só se SUCCEEDED → **promote** atômico → HTTP 200. Em falha: rollback + **unlink** temp. Heal se crash entre commit e promote. Manter `delete_stored_file` como rede.

### P3-b — Rota Fattura

**Confirmado:** `execute_commit_fattura` + `uow.commit()` **incondicional** (~1337–1350), igual Ordine (~1191–1199).

**Ambos entram na fatia 2R-b:** commit só se `SUCCEEDED`; senão rollback + cleanup FS. Sem “se”.

### Escopo 2R-b (V4)

Só: transação + ledger + filesystem honesto (Ordine **e** Fattura).  
Fora: reextract UI, readiness, PendencyList, Catalog, 3A, 020.

---

## Próxima etapa lógica

1. **Ricardo ratifica V1** (2/3/4 sem popular itens = mortas) **e V2** (confirm A vs B).
2. Autorizar **RUX-2R-b** (V3: all-or-nothing + temp-promote + gate Ordine+Fattura) **antes** de migration nullable OrderItem.
3. Só depois: implementar opção (1) apertada (RUX-3B / Orders).

## PROIBIDO agora

Implementar; migrations; aplicar 020; iniciar 2R-b/3A/3B; J#6.

```text
DOC_DELTA
- Updated: docs/v2/etapa-j3/J3_RUX_V1V3_ADVISOR_HANDOFF.md; J3_EXECUTION_PLAN.md; ROADMAP_V2_EPIC.md; plan mestre j3-rux
- Evidence: este handoff
- Roadmap status: 0.5.82 — V1–V3 Planning DONE; aguarda ratificação Ricardo
- Next TODO: Ricardo ratifica V1+V2 (confirm A vs B); depois auth RUX-2R-b
- Return to advisor: docs/v2/etapa-j3/J3_RUX_V1V3_ADVISOR_HANDOFF.md
```
