# J3-RUX — RUX-3C-fix (runtime Ordine contraditório) — Advisor handoff

| Campo | Valor |
|---|---|
| Etapa | **RUX-3C-fix** — diagnóstico + correção pós-falha de aceite manual |
| Status | **DONE** (gates desta rodada) — devolver ao advisor / Ricardo retest |
| Data | 2026-08-07 |
| Alembic | **021** (inalterado) |

---

## D1 — ANTES da correção (obrigatório)

### 1) Uvicorn 8081 reiniciado após 3B-2a?

**NÃO.** Processo PID antigo: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8081` **sem `--reload`**, **StartTime = 06/08/2026 15:52:11**.  
3B-2a/2b entraram em 07/08 — o processo **não** carregava esse código.

Precedente do badge “DB —”: **mesmo padrão** (processo servindo código velho).

### 2) Build frontend servido

| | Valor |
|---|---|
| HTML em 8081 (antes) | `index-DWT-hLuH.js` (= dist 3B-2b do dia) |
| Conclusão FE | Frontend **atual**; contradição vinha do **backend stale** |

Após rebuild desta fatia: `index-DxP1I1he.js` (servido e confirmado).

### 3) Preview API cru — documento #11 (ANTES do restart)

`GET /api/ingestion/documents/11/preview-commit` no 8081 stale:

```json
{
  "document_id": 11,
  "operations": [
    { "op_key": "store_document", ... },
    { "op_key": "create_order", "params": { "code": "589", "supplier_id": 21, ... } },
    { "op_key": "link_document", ... },
    { "op_key": "skip_item_0", "description": "Linha 0 (SKU=I.V. 2) ignorada: produto não resolvido" },
    { "op_key": "skip_item_1", "description": "Linha 1 (SKU=I.V. 1) ignorada: produto não resolvido" }
  ],
  "can_commit": false,
  "can_create_order": false,
  "blocking_reasons": [
    "Produto não resolvido na linha 0 (SKU=I.V. 2)",
    "Produto não resolvido na linha 1 (SKU=I.V. 1)"
  ],
  "human_summary": "Há linhas sem produto — vincule ou confirme criar produto."
}
```

Arquivo: [`logs/rux3c-d1-preview-doc11-raw.json`](logs/rux3c-d1-preview-doc11-raw.json)

Health do mesmo processo: `alembic_expected=019`, `alembic_head=021`, `schema_ok=false` → prova de código pré-021 em memória.

### 4) Lógica no disco vs runtime?

| | Disco (pós-3B-2a) | Runtime 8081 stale |
|---|---|---|
| Preview linhas I.V.* | `add_item` + `line_kind=COMMITMENT` | `skip_item` + “produto não resolvido” |
| `EXPECTED_ALEMBIC` | `021` | `019` |

**Não é bug de lógica nova.** É **deploy/processo velho**.  
Por isso o teste `test_rux3b2a_empty_catalog_commit_commitment_with_unit` passa (importa código do disco) e a tela do Ricardo falhava.

**Não devolve a Planning** — D1 = build/processo stale.

### Após restart (prova)

Preview doc #11 passou a emitir `add_item_*` COMMITMENT, `can_commit=true`  
([`logs/rux3c-d1-preview-doc11-after-restart.json`](logs/rux3c-d1-preview-doc11-after-restart.json)).

---

## D2 — Próximo passo Q3=(B)

- Backend correto após restart: 2× `add_item` COMMITMENT.
- UI: label  
  `Registrar N linhas de compromisso (produtos reais virão pela fatura)`.
- Botão desabilitado no screenshot do Ricardo = `can_commit=false` do backend stale (skip_item), **não** regressão Q3=B.

## D3 — Sem facilitar SKU / create-product

- Removido `pending_create_product` das células do adapter Ordine (IR novo não traz a chave).
- Removido helper morto `_pending_create_product` em `commit_commands.py`.
- Issue I.V.* → **INFO** + texto “produtos reais virão pela fatura” (sem “vincule”).
- CTA create-product no Matching Ordine já estava bloqueado; mantido.

## D4 — Zoom PDF

- Zoom re-renderizava recarregando o PDF inteiro (frágil).
- Agora: documento em cache; re-render só de página/zoom; reset 100% clicável; iframe fallback com scale visível.
- Provado: label 100% → 110% no gate.

## D5 — “Detalhes técnicos” (mínimo Ordine)

**Proposta / feito:** no caminho Ordine, **eliminado** o `<details>Detalhes técnicos</details>` (não renomear/esconder).

| Mantém | Sai de vez |
|---|---|
| Resumo Ordine | JSON cru das linhas |
| Antes de criar (só fornecedor / EAN real) | Aprovar/Rejeitar seções |
| Próximo passo | Campos raw/efetivo |
| Só se houver **ERROR** aberto: bloco “Erros que impedem…” + Ignorar c/ justificativa | Lista “Pendências técnicas 1/15” |

## D6 — Limpeza

Script único:

```text
cd v2
.\.venv\Scripts\python.exe ..\docs\v2\etapa-j3\scripts\rux3c_reset_ordine_runtime.py
```

- Só `epic_v2`; recusa `epic_v2_test`.
- Limpa fila ingestão; remove Heroe's se sem pedidos; remove ING-* DRAFT/CANCELLED vazios.
- Já executado nesta rodada (11 docs + supplier 21 + ING-589 CANCELLED).

---

## Gates (runtime Ricardo :8081 / epic_v2)

| Gate | Evidência |
|---|---|
| Preview compromisso, sem “ignorada” | `screenshots/rux-3c-fix/03-preview-compromisso.png` |
| Botão criar habilitado | mesmo + script prove |
| Pedido com 2 linhas 14600/2000 PZ | `06-pedido-compromissos.png` |
| Zoom PDF | `04-pdf-zoom.png` |
| Chromium | `149.0.7827.55` |
| Asset servido | `index-DxP1I1he.js` |
| Health | `schema_ok=true`, expected=021 |
| Script | `v2/frontend/scripts/rux3c-fix-prove.mjs` → PASS |

## Roteiro RUX-3C atualizado

1. **Reiniciar 8081** após puxar código (sem `--reload` = obrigatório restart). Conferir `/api/health` → `alembic_expected=021` e `schema_ok=true`.
2. Hard-refresh no browser (Ctrl+F5) — asset `index-DxP1I1he.js` (ou hash do dist atual).
3. Opcional limpeza: comando D6 acima.
4. Importar Ordine 589 (catálogo sem Heroes) → cadastrar fornecedor (intent) → ver preview com **2 linhas de compromisso** → criar → abrir pedido.
5. Conferir zoom − / 100% / +.
6. Confirmar: **sem** painel “Detalhes técnicos”.

## Recomendação operacional

Documentar no start do runtime: **sempre reiniciar uvicorn após merge/pull** se não usar `--reload`. Health `schema_ok=false` / `alembic_expected` ≠ head = sinal vermelho.

## DOC_DELTA

```text
DOC_DELTA
- Updated: docs/v2/etapa-j3/J3_RUX_3C_FIX_ADVISOR_HANDOFF.md; adapter/commit/UI PDF+Ordine; scripts limpeza+prove
- Evidence: docs/v2/etapa-j3/logs/rux3c-d1-preview-doc11-*.json; screenshots/rux-3c-fix/; logs/rux3c-fix-pytest-full.txt (452 passed)
- Roadmap status: (atualizar se advisor fechar) — próxima = reteste manual Ricardo
- Next TODO: Ricardo reexecuta RUX-3C no runtime dele após restart confirmado
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3C_FIX_ADVISOR_HANDOFF.md
```
