# J3-RUX — C1–C5 pós-B1 Planning — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | Isolamento RUX-3A + gate drift + B2–B5 (pós decisão **não aplicar 020**) |
| Status | **DONE** (com ressalva C2 Modelo B — ver abaixo) |
| Data | 2026-08-06 |
| Runtime | `8081` · `epic_v2` · alembic **019** · Importação **#7** |
| Chromium (aceite G6) | **Chrome/144.0.7559.236** (Cursor/Electron userAgent) |

**Decisão Planning:** NÃO aplicar migration 020. Árvore = head **019**.

---

## C1 — Isolamento RUX-3A (saída da árvore de execução)

| Item | Destino |
|---|---|
| Migration `020_catalog_rux_identity_refs.py` | `docs/v2/etapa-j3/_wip_isolated_rux3a_rux2rb/` (**fora** de `alembic/versions`; não aplicar, não apagar) |
| `Supplier.tax_id`, `SupplierProductRef`, `code_kind`, fingerprint, `product_sku_seq` / `allocate_next_sku` | Removidos do Catalog ORM/commands/queries/routes/public |
| MatchingPanel `tax_id` | Removido do payload create-supplier |
| Adapter refs AUTO/SUGGEST + `_safe_catalog` | Removidos; I.V.* → `UNMATCHED_SKU` (Q3=B) |
| Testes `test_catalog_rux3a.py` | Movidos para WIP isolado |

**Prova:** `alembic heads` → `019 (head)`; `list_suppliers` OK sem savepoint; `_safe_catalog` ausente no tree.

---

## C2 — Modelo B / reextract

| Item | Ação |
|---|---|
| **reextract** route | **Isolado** — retorna `501 reextract_not_authorized`; impl. permanece em `staging_commands` (WIP) |
| Testes reextract / Modelo B tx | Movidos para `_wip_isolated_rux3a_rux2rb/` |
| **Modelo B `begin_nested` em `execute_commit`** | **PARE — revisão formal** |

**Evidência do PARE:** savepoints + ledger PARTIAL estão entrelaçados no caminho de commit (não no preview `skip_order` do 2R-a). Remover `begin_nested` sem redesenhar all-or-nothing / status do attempt corrompe o ledger e os testes de PARTIAL. Isolamento completo = **RUX-2R-b** com autorização + revisão + teste.  
**RUX-3A removido do commit:** `tax_id=` e `upsert_supplier_product_ref` / `sku=None` — fora.  
**Ainda na árvore (NÃO desta fatia):** `begin_nested` + semântica PARTIAL em `commit_commands.execute_commit`.

---

## C3 — Drift visível

- Health: `alembic_head`, `alembic_expected=019`, `schema_ok`; status `degraded` se drift.
- Lifespan (não-test): `assert_schema_revision` — falha alta se aplicado ≠ 019.
- Badge tooltip: inclui `alembic 019`.

---

## C4 — B2–B5

| Item | Status |
|---|---|
| B2 total_document guardado + L4 `MATH_LINE_VAT_NATURE` | Restaurado (sem L3/SCONTI completo) |
| B3 golden positivo i3+i4 | Esta rodada: **60 passed**; diff em `logs/c1c5-golden-diff.md` |
| B4 fila | #1–#3/#6 REJECTED; **#7** = único DRAFT bom **Ordine 589**; #4/#5 DRAFT lixo (sem order_number) |
| B5 Chromium | **144.0.7559.236** |

**Gate UI #7:** 1 pendência operador (fornecedor); desc. legíveis; data **04/06/2026**. Screenshot: `screenshots/j3-rux-c1c5-ordine-589.png`.

---

## C5 — Governança (nova regra)

Todo handoff de fatia declara explicitamente o que está na árvore em execução e **NÃO** pertence à fatia entregue.

### WIP na árvore — NÃO desta fatia

1. **Modelo B** (`begin_nested` + PARTIAL) em `commit_commands.execute_commit` — RUX-2R-b.
2. **`staging_commands.reextract_document`** (função viva; route gated 501) — RUX-2R-b.
3. OpenAPI Catalog: alinhado pós-C1 (`Supplier*` sem `tax_id`/refs). `tax_id` restante no OpenAPI = **Payee** (customs) — legítimo; não é drift Catalog.
4. Docs DRAFT **#4/#5** sem `order_number` (lixo de outras tentativas). **Não** contradiz C4: o gate C4 é “só **#7** DRAFT bom do **Ordine 589**”; #4/#5 são DRAFTs sem 589.

---

## Gates

| Gate | Prova |
|---|---|
| alembic aplicado = esperado | `019` = `EXPECTED_ALEMBIC_REVISION`; `alembic heads` = 019 |
| list_suppliers sem savepoint | OK em epic_v2 |
| `_safe_catalog` removido | grep limpo no adapter |
| Ordine 589 reimport | Doc **#7**; 1 pendência fornecedor; unsqueeze OK; 04/06/2026 |
| pytest i3+i4 | 60 passed (`logs/c1c5-pytest-i3-i4.txt`) |
| Badge alembic | health + tooltip |
| Screenshot + Chromium | paths acima; Chrome/144.0.7559.236 |

---

## Próxima etapa lógica

1. **PARAR** — não iniciar RUX-2R-b / RUX-3A sem autorização + replanejamento pós-Q3=(B).
2. Revisão formal **Modelo B** (RUX-2R-b) quando autorizada.
3. RUX-3A redesenhada (tax_id sozinho vs refs) — só com migration nova, nunca reaplicar 020 como estava.

## Recomendação

Aceitar esta fatia com a ressalva explícita do Modelo B ainda vivo no commit path (gating de reextract OK; isolation completa do Modelo B adiada por risco de ledger).

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; plan mestre j3-rux
- Evidence: docs/v2/etapa-j3/J3_RUX_C1C5_ADVISOR_HANDOFF.md; screenshots/j3-rux-c1c5-ordine-589.png; logs/c1c5-*; _wip_isolated_rux3a_rux2rb/
- Roadmap status: 0.5.80 — C1–C5 DONE; Modelo B residual = RUX-2R-b
- Next TODO: PARAR — aguardar autorização RUX-2R-b / replanejamento RUX-3A
- Return to advisor: docs/v2/etapa-j3/J3_RUX_C1C5_ADVISOR_HANDOFF.md
```
