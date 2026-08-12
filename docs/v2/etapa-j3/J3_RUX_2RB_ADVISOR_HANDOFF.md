# J3-RUX — RUX-2R-b — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | **RUX-2R-b** (transação + ledger + filesystem honesto) |
| Status | **DONE** (gates de código/teste desta fatia) |
| Data | 2026-08-06 |
| Escopo | Ordine + Fattura commit: all-or-nothing; temp→promote; trilha de falha fora da UoW |
| Fora | reextract UI (501), readiness, PendencyList, Catalog, RUX-3A, mig 020, OrderItem nullable, `line_kind` (só documentado) |

---

## WIP na árvore — NÃO desta fatia (regra C5)

1. `staging_commands.reextract_document` + rota **501** (`reextract_not_authorized`)
2. Migration **020** em `docs/v2/etapa-j3/_wip_isolated_rux3a_rux2rb/` — **não aplicar**
3. Nullable `OrderItem.product_id` / `line_kind` — **desenho V2 ratificado; implementar só com auth RUX-3B**
4. Numerario / XLSX / Dossier ainda usam semântica PARTIAL própria (não tocados)
5. Policy C1 ainda pode criar Order **vazia** — item de higiene (não corrigido nesta fatia)

---

## D1 / D2 (antes do código — evidência)

### D1 — Attempts PARTIAL existentes

Consulta: `docs/v2/etapa-j3/logs/d1_partial_attempts_query.py`

| Banco | Resultado |
|---|---|
| `epic_v2` | `attempts_by_status = []`; `partial_or_unknown = 0` |
| `epic_v2_test` | tabela criada/derrubada por sessão de teste — sem dado operacional |

**Decisão:** sem migração de dados; sem tradução na leitura. Valor `PARTIAL` permanece no CHECK/modelo compartilhado (numerario/xlsx/dossier). Ordine/Fattura **deixam de emitir** PARTIAL.

### D2 — Trilha da falha vs rollback

**Escolha (i):** registro da falha **fora** da transação (sessão separada em `commit_failure.record_commit_failure`).

- (ii) é impossível: flush na mesma UoW some no rollback.
- Após rollback: attempt `FAILED` + ops (`FAILED` na que quebrou; `SKIPPED` + `rolled_back` nas que haviam “sucedido” no flush); Audit `commit_failed`.
- **Retry:** mesma `operation_key` + fingerprint + status ≠ SUCCEEDED → limpa ledger e **reexecuta do zero** (nada de domínio sobreviveu). SUCCEEDED → replay idempotente.

---

## Entregas

| Item | Evidência |
|---|---|
| Sem `begin_nested` em `execute_commit` / Fattura path | `commit_commands.py`, `fattura_commit_commands.py` |
| Gate: `uow.commit()` só se SUCCEEDED (Ordine + Fattura) | `routes.py` |
| FS: write `.pending` → commit DB → promote; falha → unlink; heal em `resolve_content_path` | `documents/public.py` |
| Trilha fora da UoW | `ingestion/commit_failure.py` |
| Gate falha injetada Ordine | `test_commit_injected_failure_persists_nothing_then_retry_succeeds` |
| Gate Fattura (invoice duplicada) | `test_policy_a_duplicate_invoice_is_all_or_nothing` |
| pytest i3+i4 | **62 passed** — `logs/rux2rb-pytest-i3-i4-final.txt` |
| Diff goldens | `logs/rux2rb-golden-diff.md` (goldens IR **NONE**; asserts commit deliberados) |

---

## Condições V2 (registradas; implementar só com auth 3B)

| ID | Condição |
|---|---|
| **(a)** | Usar `line_kind` **explícito** — não tratar `product_id IS NULL` como sinônimo de compromisso |
| **(b)** | Ao `confirm_order` com linhas de compromisso: **aviso UI** + **Audit** (variante C sem bloqueio B) |

**Higiene (não nesta fatia):** Policy C1 criar Order vazia deixa de ser caso normal sob opção (1) — tratar como anomalia quando 3B/Fattura hygiene for autorizada.

---

## Ratificações já aplicadas nesta execução

- V1: header-only é **terminal** sem popular itens (não “impossível estrutural”).
- V2: opção (1) apertada + confirm variante A (+ condições a/b acima).
- V3: temp→promote + gate Ordine **e** Fattura.

---

## Riscos / pendências

- Retry de FAILED reexecuta do zero — operador vê motivo no ledger/Audit do attempt FAILED; histórico acumula no Audit.
- Crash entre commit DB e promote: heal na leitura (`resolve_content_path`); `delete_stored_file` permanece como rede.
- `begin_nested` ainda existe em `ingestion/commands.py` (fora do path de commit Ordine/Fattura) — não tocado.

---

## Próxima etapa lógica recomendada

1. Advisor/Ricardo: aceitar RUX-2R-b.
2. Autorizar **migration OrderItem nullable + `line_kind` + guards** (início de RUX-3B) — **não** iniciar sem auth explícita.
3. RUX-3A / mig 020 / J#6 / reextract UI: **não** iniciar.

---

## DOC_DELTA

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; docs/v2/etapa-j3/J3_RUX_2RB_ADVISOR_HANDOFF.md
- Evidence: docs/v2/etapa-j3/logs/rux2rb-pytest-i3-i4-final.txt; docs/v2/etapa-j3/logs/rux2rb-golden-diff.md; docs/v2/etapa-j3/logs/d1_partial_attempts_query.py
- Roadmap status: RUX-2R-b DONE; próxima = auth OrderItem nullable / RUX-3B (ou parar)
- Next TODO: Aguardar aceite; auth explícita para migration OrderItem + line_kind (RUX-3B)
- Return to advisor: docs/v2/etapa-j3/J3_RUX_2RB_ADVISOR_HANDOFF.md
```
