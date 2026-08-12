# J3-RUX — RUX-3F-POST-2 ADVISOR HANDOFF

| Campo | Valor |
|---|---|
| Etapa | **RUX-3F-POST-2** |
| Status | **DONE** (read-only + teste; **BLOCKER V5** aberto) |
| Data | 2026-08-10 |
| Escopo | V5 — revalidação math após correção manual |
| epic_v2 / Order 589 | **não tocados** |
| Conserto | **NÃO** (mandato) |

---

## V5 — Math re-roda após PATCH qty?

### Código (investigação)

| Path | Comportamento |
|---|---|
| Extração | `ordine_heroes_v1.run_adapter` → `_validate_math` → seeds issues |
| `correct_row` (`staging_commands.py`) | Escreve `cells_json` + audit; **zero** chamada a `_validate_math` / criação de issue |
| Commit | Bloqueia só se já existirem `OPEN` + `severity=ERROR`; **não** revalida math |

### Prova (`epic_v2_test`)

Teste: [`v2/tests/test_ingestion_rux3f_post2_v5.py`](../../v2/tests/test_ingestion_rux3f_post2_v5.py)  
Log: [`logs/rux3f-post2-v5-pytest.txt`](logs/rux3f-post2-v5-pytest.txt)

| Passo | Resultado |
|---|---|
| 1. Seed Ordine 589 + extract | Sem `MATH_*` ERROR |
| 2. PATCH qty `14600` → `99999`, **line_total PDF intacto** | 200 OK |
| 3. Issues após PATCH | **`math_errors_after_patch: []`** |
| 4. Commit | **200 SUCCEEDED** |
| 5. OrderItem | **quantity = 99999** gravada |

Caracterização estável: o teste **passa** enquanto o buraco existir (assert `math_after == []` + commit SUCCEEDED). Se alguém implementar revalidação, o teste falha e força atualizar este handoff.

### BLOCKER V5

**Buraco:** correção manual de qty que contradiz o total de linha impresso no PDF **não** gera `MATH_LINE_TOTAL_MISMATCH` (nem equivalente) e **não** bloqueia o commit. O operador (ou API) consegue criar pedido com quantidade inconsistente com o documento **em silêncio**.

A validação math é **somente no momento da extração**. Pós-D8/I3, editar chega à Order sem segunda passagem de alarme.

### Nota UI (não mitiga o BLOCKER)

`OrdineSummaryPanel.saveRow` recalcula `line_total = qty×price` no PATCH da UI — nesse caminho o mismatch **linha** some porque a célula é alterada junto. Mesmo assim:
1. o buraco API/client permanece (PATCH só qty);
2. divergência vs **total impresso / bases do PDF** (`MATH_TOTAL_MISMATCH` / `MATH_LINES_VS_TAX_BASES`) também **não** re-dispara após edição coerente qty+line_total (ex. 14601 no I3).

### Proposta (só após evidência — **não implementar**)

Correção legítima deve continuar possível. Saída provável alinhada ao advisor: **avisar sem bloquear** (WARNING/Notice) quando IR pós-edição divergir do PDF; ou revalidar math no PATCH/commit como aviso. Bloquear por defeito seria errado se o operador tiver razão contra o extrator.

---

## Fora / proibições respeitadas

Sem Fattura, DDT, exposição, Payable, migration, 3A/020/J#6, conserto de produto.

## Próxima etapa lógica

1. Advisor decide severidade/tratamento do **BLOCKER V5** (aviso vs revalidação).  
2. Em paralelo: decisão Reporting vs RUX-4 (POST).  
3. Sem 3A/020/J#6.

```text
DOC_DELTA
- Updated: docs/v2/etapa-j3/J3_RUX_3F_POST2_ADVISOR_HANDOFF.md; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; ROADMAP_V2_EPIC.md
- Evidence: v2/tests/test_ingestion_rux3f_post2_v5.py; docs/v2/etapa-j3/logs/rux3f-post2-v5-pytest.txt
- Roadmap status: 0.5.93 → 0.5.94 RUX-3F-POST-2 DONE; BLOCKER V5 aberto
- Next TODO: decisão advisor V5 (aviso sem bloquear?) + Reporting vs RUX-4
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3F_POST2_ADVISOR_HANDOFF.md
```
