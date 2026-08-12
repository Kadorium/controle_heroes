# J3-RUX — B1 schema/WIP drift — Advisor handoff (PARAR → Planning)

| Campo | Valor |
|---|---|
| Etapa | Correção curta pós-2R-a — **B1 levantamento** |
| Status | **BLOCKED_FOR_PLANNING** (WIP não autorizado ativo no runtime) |
| Data | 2026-08-06 |
| Runtime | `8081` · `epic_v2` · alembic **019** |

**Aceite 2R-a (parcial):** unsqueeze/raw, C4 dual-form, A1/A2, skip_order, governança — **ACEITO**.  
**Não aceito (ainda no tree):** remoção `MATH_TOTAL_MISMATCH`, `_safe_catalog`, golden por ausência, i4 não re-rodada nesta correção.

**B2 / B3 / B4 / B5:** **NÃO EXECUTADOS** nesta rodada — o B1 mostrou WIP espalhado; regra: *PARE e devolva para Planning*.

---

## B1.1 — Quem consulta `suppliers.tax_id`?

| Camada | Path | Origem |
|---|---|---|
| Migration | [`v2/alembic/versions/020_catalog_rux_identity_refs.py`](../../v2/alembic/versions/020_catalog_rux_identity_refs.py) | Cabeçalho: **“RUX-3A — Catalog identity refs (tax_id, SKU sequence, supplier_product_refs)”** |
| Model ORM | [`v2/app/catalog/models.py`](../../v2/app/catalog/models.py) — coluna `Supplier.tax_id` + índice parcial | Mesma campanha |
| Commands/repo/routes | `catalog/commands.py`, `repository.get_supplier_by_tax_id`, `routes` create supplier | H-EXEC-04 / RUX-3A |
| FE MatchingPanel | `tax_id: createCode.trim()` no intent create supplier | RUX-3A wiring |
| Adapter Ordine | **Não** chama `get_supplier_by_tax_id` | `match_catalog` usa `list_suppliers(db, q=digits)` (name/code ILIKE) |

**Como chegou ao tree em execução:** código + migration **020** entraram no working tree na campanha RUX-1R/3A (WIP), **sem** aplicar 020 em `epic_v2` e **sem** autorização na fatia 2R-a. O Roadmap declara head **019**; a migration 020 existe no disco mas **não** está no `alembic_version` de `epic_v2`.

**Por que `list_suppliers` quebra sem usar tax_id no WHERE:** o ORM faz `SELECT` de **todas** as colunas mapeadas, incluindo `tax_id`. Postgres: `coluna suppliers.tax_id não existe` → qualquer listagem de supplier falha.

---

## B1.2 — WIP não autorizado ativo no runtime 8081

| Artefato | No tree? | Ativo em 8081? | Schema 019? | Nota |
|---|---|---|---|---|
| `020` tax_id + `product_sku_seq` + `supplier_product_refs` | SIM | Código SIM / DB NÃO | Drift | Refs/fingerprint/SKU seq |
| `SupplierProductRef` + `code_kind` EAN/SUPPLIER_CLASS | SIM | Chamado em `match_catalog` | Tabela **ausente** | Falha engolida por `_safe_catalog` |
| `description_fingerprint` | SIM (`catalog/normalization.py`, match SUGGEST) | Só se refs existirem | N/A | Código vivo |
| Modelo B / `begin_nested` em `commit_commands` | SIM | SIM no commit path | Ledger 018+ | RUX-2R-b territory |
| `reextract` route + `staging_commands.reextract_document` | SIM | Endpoint montado | — | RUX-2R-b |
| `_safe_catalog` savepoint (2R-a) | SIM | SIM | Contorno | **Não autorizado** |
| Sequence SKU `product_sku_seq` | Migration 020 | Não criada no DB | Drift | |

**Veredito:** WIP **espalhado e ativo** (Catalog 020 + matching refs + reextract + Modelo B + savepoint). Deixa de ser “correção curta”.

---

## B1.3 — Schema `epic_v2` vs alembic head

| | |
|---|---|
| `alembic_version` | **019** |
| Migration no disco mais nova | **020** (não aplicada) |
| Roadmap “Alembic head” | ainda cita `019_ingestion_metrics_events` |

**Drift além de `tax_id`:**

| Objeto | Model/código | DB `epic_v2` |
|---|---|---|
| `suppliers.tax_id` | presente | **ausente** |
| `supplier_product_refs` | model + queries | **tabela ausente** (`to_regclass` → null) |
| `product_sku_seq` | 020 | **ausente** |
| `products` cols | sku, description, … | alinhado (sem cols 020 extras) |
| `ingestion_fields` | API “effective_value” é derivado | DB tem raw/normalized/corrected (ok) |

Não há Heroe's no catálogo operacional: 20 suppliers, todos E2E/FX/BILL — **nenhum** nome/código Heroes/PI.

---

## B1.4 — Cenário duplicata (confirmar/refutar)

**Mecanismo (CONFIRMADO):** com `_safe_catalog`, falha de ORM em `list_suppliers` → `[]` → `SUPPLIER_NOT_FOUND` → UI “ainda não cadastrado” → operador pode **criar duplicata** de um fornecedor que **já existiria** por nome (ex. `Heroe's Srl`).

**Estado atual dos dados (REFUTADO para Heroe's hoje):** Heroe's **não** está cadastrada em `epic_v2`. O “não cadastrado” do doc #3 é factual para este DB — o risco é **latente** assim que alguém cadastrar Heroe's (ou qualquer supplier) enquanto o model exigir `tax_id` e o DB não tiver a coluna.

**Nuance:** mesmo com 020 aplicada, o adapter Ordine **ainda não** faz match por `get_supplier_by_tax_id(PI)`; usa `list_suppliers(q=digits)` em name/code. O bug imediato é SELECT ORM × schema 019, não “match fiscal que falha”.

---

## L4 (só resposta factual — B2 não executado)

`MATH_LINE_VAT_NATURE` **já existia** em `_validate_math_heroes_pdf` **antes** da remoção em 2R-a (camada da campanha RUX math / “two-layer”, não check legado I3 original). Foi **removida** em 2R-a junto com L3/legacy. Mesma lógica do Ricardo para `MATH_TOTAL_MISMATCH`: “fora do escopo” ≠ “apagar check preexistente”.

---

## Proposta B1 (NÃO EXECUTADA — aguarda OK)

**Recomendada:** remover `_safe_catalog` / `begin_nested` engolidor.

**Degradação explícita (sem migration Catalog nesta fatia):**

1. Em `list_suppliers` / queries Catalog usadas pelo adapter: **não** selecionar `tax_id` se a coluna não existir **ou**
2. Preferível e mais limpo: **carregar Supplier só com colunas 019** no caminho de matching até Planning decidir aplicar/reverter 020 — ex. `db.query(Supplier.id, Supplier.code, Supplier.name, …)` sem mapear `tax_id` nesse path; **ou** feature-flag `catalog_rux_identity` off quando alembic &lt; 020.
3. Log/issue **visível** se Catalog RUX path indisponível: não silêncio (`CATALOG_SCHEMA_DRIFT` INFO/WARNING), em vez de fingir “supplier not found”.
4. **Não** aplicar 020 sem autorização (proibido nesta ordem).
5. **Não** reverter 020 do tree sem decisão Planning (pode ser WIP intencional a isolar).

**Alternativa Planning:** aplicar 020 só em `epic_v2_test` + política explícita; ops `epic_v2` fica 019 até aceite RUX-3A — código Catalog RUX não deve rodar contra 019.

---

## B2–B5 (adiados)

| Item | Motivo |
|---|---|
| B2 total_document guardado | Adiado — Planning primeiro |
| B3 golden positivo + i3+i4 | Adiado — não citar baseline obsoleto; re-rodar após B2 |
| B4 triplicata #1/#2/#3 | Adiado — docs: #1 REJECTED, #2 DRAFT stale, #3 DRAFT bom |
| B5 Chromium versão G6 | Adiado |

**Docs 589 atuais:** #1 REJECTED · #2 DRAFT (IR velho) · #3 DRAFT (pós-2R-a). Operador ainda vê #2+#3 na fila se filtrar por DRAFT.

---

## Próxima etapa lógica

1. **Planning** decide destino do WIP Catalog 020 / RUX-3A no tree vs runtime 019.  
2. Só então: OK para remover `_safe_catalog` + degradação explícita.  
3. Em seguida (autorização): B2 → B3 (i3+i4) → B4 → B5.  
4. RUX-2R-b continua **não autorizado**.

```text
DOC_DELTA
- Updated: este handoff
- Evidence: alembic 019; suppliers sem tax_id; supplier_product_refs ausente; 020 no disco
- Roadmap status: UNCHANGED nesta rodada (bloqueio Planning)
- Next TODO: Planning — isolar/reverter/aplicar 020 + autorizar remoção _safe_catalog
- Return to advisor: docs/v2/etapa-j3/J3_RUX_B1_SCHEMA_DRIFT_ADVISOR_HANDOFF.md
```
