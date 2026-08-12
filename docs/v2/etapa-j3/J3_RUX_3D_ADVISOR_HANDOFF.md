# J3-RUX — RUX-3D (desbloquear jornada + completar tela) — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | **RUX-3D** |
| Status | **DONE** (gates desta fatia) |
| Data | 2026-08-07 |
| Alembic | **021** (inalterado) |

---

## P0 — Order 589 já existia?

**SIM.** Em `epic_v2` no momento do diagnóstico:

| Campo | Valor |
|---|---|
| id | **22** |
| code | **ING-589** |
| status | **DRAFT** |
| Linhas | **2 COMMITMENT** — I.V. 2 qty **14600** PZ €50; I.V. 1 qty **2000** PZ €50 |

A jornada **já tinha sido concluída com sucesso** numa tentativa anterior (doc IR 12).  
O “beco” do Ricardo ao reimportar era colisão com esse pedido — não falha de COMMITMENT.

---

## Origem do prefixo ING- (antes de mudar)

Hardcoded em `commit_commands.execute_commit`:

```python
code=f"ING-{order_number}"
```

com `external_ref=order_number`.

**Razão histórica (fraca):** namespacing vs pedido manual + comentário de teste I3 sobre unicidade.  
**Não resolve reimport:** segundo commit do mesmo 589 ainda colide em `ING-589`.  
**Vaza “ingestão” para dado de negócio.**

**Decisão D7:** código padrão = número do documento (`589`). Preview já listava `code=order_number`; execute agora alinhado. Legado `ING-{n}` ainda é detectado na colisão.

---

## D7 — Código editável + colisão operacional

- Campo **Código do pedido** no bloco “Próximo passo” (edita `order_number` via `corrected_value`).
- Colisão **antes** de `store_document` → `commit_order_code_exists` (409) + `details.order_id/order_code`.
- UI: “O pedido X já existe” · **Abrir pedido existente** · **Criar com outro código** · mantém “Nada foi gravado”.
- Provado no runtime (screenshots 03/04; API 409 com details).

## D8 — Edição no Resumo (regressão D5)

Restaurada **só UI** sobre contrato existente (`correctIngestionField` / `patchIngestionRow` / add / delete row):

- Cabeçalho: número, data, moeda, total  
- Linhas: descrição, qty, unidade, preço; remover; adicionar  
- Sem JSON / raw-efetivo / aprovar seção  

Provado: qty 14600 → 14601 no Resumo (screenshot 02).

## D9 — Exclusão definitiva

`DELETE /api/ingestion/documents/{id}`:

- Remove IR + ledger de tentativas se **não** houver `create_order` SUCCEEDED  
- Se já criou pedido → 409 `document_delete_blocked` com explicação  

UI: botão **Excluir** na fila + “Descartar / excluir” no workspace.  
Provado: DELETE 14 → 204; DELETE 12 (já criou pedido) → 409 bloqueado.

## D10 — Linguagem da tela Ingestão

Fila + Intake: subtítulo/CTAs/status/tipos em português; removidos MIME, hash/reuse, occ #, Adapter, Occurrence, DRAFT/REJECTED crus, ORDINE_COMPRA → “Pedido de compra”.

---

## Gates

| Gate | Evidência |
|---|---|
| Colisão abre existente + outro código | `screenshots/rux-3d/03-colisao-codigo.png`, `04-criado-outro-codigo.png` |
| Editar qty no Resumo | `02-edicao-linha.png` |
| Excluir importação | API 204 + UI Excluir; `05-excluir-importacao.png` |
| Fila sem jargão técnico | `01-fila-linguagem.png` |
| Chromium | `149.0.7827.55` |
| Asset | `index-DBFV8BrW.js` |
| pytest | **452 passed** — `logs/rux3d-pytest-full.txt` |

## Roteiro RUX-3C atualizado

1. `/api/health` → `schema_ok=true`, expected **021**; reinicie 8081 se não. Hard refresh.  
2. Se `ING-589` / `589` já existir: na colisão use **Abrir existente** ou **outro código**.  
3. Corrija qty/descrição no **Resumo** se necessário.  
4. Código do pedido editável no **Próximo passo**.  
5. Importações sem pedido: **Excluir** some da fila.  
6. Tela Ingestão deve ler em português operacional (sem MIME/hash/adapter).

## DOC_DELTA

```text
DOC_DELTA
- Updated: ROADMAP_V2_EPIC.md (0.5.88); J3_EXECUTION_PLAN.md; J3_RUX_3D_ADVISOR_HANDOFF.md
- Evidence: docs/v2/etapa-j3/screenshots/rux-3d/; logs/rux3d-pytest-full.txt
- Next TODO: aceite advisor / reteste Ricardo
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3D_ADVISOR_HANDOFF.md
```
