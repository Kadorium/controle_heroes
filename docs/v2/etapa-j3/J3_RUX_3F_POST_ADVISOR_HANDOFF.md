# J3-RUX — RUX-3F-POST ADVISOR HANDOFF

| Campo | Valor |
|---|---|
| Etapa | **RUX-3F-POST** |
| Status | **DONE** (read-only; zero mudança de produto) |
| Data | 2026-08-10 |
| Runtime DB | `epic_v2` @ `localhost:5433` (só SELECT) |
| Order 589 | **preservada** (não tocada) |

---

## V1 — Cadeia Ordine → DDT → Fattura?

### Inventário

| Artefacto | Existe no corpus? |
|---|---|
| PDF/extract tipado **DDT** (remessa italiana) | **NÃO** — zero ficheiros `*DDT*` no repo |
| Adapter `ddt_*` | **NÃO** — só `packing_list_detail_v1` / `packing_list_grouped_v1` + fattura/ordine/… |
| Packing List 202/328/181 | **SIM** (fixtures + extracts) — **não** são DDT |
| DDT **389** / **594** (citados nas Fatturas) | **NÃO** presentes como documentos |

### Literais

Fattura 202:

```text
DDT 389 - 30/03/2026
```

Fattura 328:

```text
DDT 594 - 18/05/2026
```

Packing List 202 / Grouped 202 / PL 328: **nenhuma** ocorrência de `Ordine` / `Vs. Ordine` / `Ordine n.` / PO / `589` nos extracts (`docs/v2/_tmp_pdf_extract/PackingList*.txt`). Header PL usa o **número da fatura** (`202` / `328`), não o número do DDT.

Adapter Fattura: extrai `ddt_ref` apenas (`fattura_heroes_v1`). Adapters de Packing List: **não** extraem referência a Ordine/DDT/PO.

### Fattura rastreável a Ordine conhecido?

**NÃO** no repo. `corpus_589` = só `Ordine_589.pdf`. Fatturas 202/328/181 são dossiers de remessa/SKU EAN, não de compromisso I.V. 589. P0 já registava: *“Ordine correspondente à Fattura 202 | I4 sem pedido nativo no corpus”*.

### Veredito âncora RUX-4

Hipótese advisor **não confirmada** nesta amostragem: a Fattura cita DDT, mas **não há DDT no corpus** para provar salto DDT→Ordine. Packing List **≠** DDT e **não** cita Ordine.

**Âncora técnica construível via corpus atual: NÃO.** Reconciliação compromisso↔EAN continua a depender de **regra de negócio do Ricardo** e/ou de **obter amostras reais de DDT** (389/594 ou DDT ligado a 589). Custo RUX-4 **não** cai com base nestes PDFs.

---

## V2 — MATH_TOTAL_MISMATCH após Ajuste 3

| Pergunta | Resposta |
|---|---|
| Continua avaliado no fluxo Ordine? | **SIM** — `ordine_heroes_v1._validate_math` → `_validate_math_heroes_pdf` |
| `total_document` do PDF ainda lido/comparado? | **SIM** — extraído no header; comparado a `imponibile+esenti` quando IMPOSTE/SCONTI/Spese=0 |
| Operador vê divergência? | **SIM** — issue `severity=ERROR` entra em **“Erros que impedem criar o pedido”** (`openBlockingErrors`); também `ordine-math-known-false`; commit bloqueia (`commit_blocked_by_issues`) |

### Prova (script read-only)

`docs/v2/etapa-j3/logs/rux3f_post_v2_math_proof.py` sobre `Ordine_589.pdf`:

- Golden: `total_document=830000`; codes = `MATH_EXPORT_N31` (INFO) — sem mismatch.
- `total_document` forçado a `1.00` → **`MATH_TOTAL_MISMATCH` ERROR**  
  mensagem: `Total documento (1.00) difere de imponibile+esenti (830000.00) com IMPOSTE/SCONTI/Spese=0`
- Qty linha forçada a `99999` (line_total PDF intacto) → **`MATH_LINE_TOTAL_MISMATCH` ERROR**

### Nuance (não BLOCKER)

Ajuste 3 fez o **Resumo** mostrar Σ linhas (não o total impresso editável). Isso remove o dual visual no Resumo — a “soma bate consigo” **no card Total**. O alarme **não morreu**: permanece no IR + painel de erros bloqueantes. Trocar desonestidade por ponto cego total: **refutado**.

Nota fina: `MATH_TOTAL_MISMATCH` compara total impresso × bases fiscais, não × Σ linhas; erro de qty vs line_total do PDF é outro código (`MATH_LINE_TOTAL_MISMATCH`), também ERROR e visível.

**Veredito V2: PASS — sem BLOCKER.**

---

## V3 — Suíte completa

| Métrica | Valor |
|---|---|
| Comando | `pytest -q` em `v2/` |
| Resultado | **456 passed**, 1 warning |
| Log | [`logs/rux3f-post-pytest-full.txt`](logs/rux3f-post-pytest-full.txt) |
| Ref. RUX-3E | 455 → **+1** (testes RUX-3F) |

Nada quebrado. Sem conserto.

---

## V4 — Quem confirmou Order 31?

| Campo | Valor |
|---|---|
| `audit_log.id` | **913** |
| `actor_id` | **`1`** |
| User | **`admin@epic.com.br`** / `Administrador` |
| `action` / `reason_code` | `confirm` / `ORDER_CONFIRM_WITH_COMMITMENT` |
| `created_at` | `2026-08-10 14:30:06` (UTC−3) |

A verificação Browser RUX-3F (T1–T3) **encontrou** o pedido já Confirmado e **não** executou confirm. Não há evidência nesta fatia de POST `/confirm` pelo agente. Com login operacional partilhado `admin@…`, a atribuição coerente com o aceite humano é o **Ricardo** — não mutação do agente POST. Só relatório.

---

## Próxima etapa lógica (sugestão)

1. Decisão advisor: **exposição Reporting** vs **RUX-4** (ainda sem âncora DDT no corpus; pedir DDT real se quiser baixar custo).  
2. Opcional UX menor (não urgente): mostrar no Resumo o total impresso do PDF **read-only** ao lado da Σ linhas quando divergirem — alarme já existe.  
3. **Sem** 3A / 020 / J#6 / Fattura import nesta porta.

```text
DOC_DELTA
- Updated: docs/v2/etapa-j3/J3_RUX_3F_POST_ADVISOR_HANDOFF.md; docs/v2/etapa-j3/J3_EXECUTION_PLAN.md; ROADMAP_V2_EPIC.md
- Evidence: docs/v2/etapa-j3/logs/rux3f-post-pytest-full.txt; docs/v2/etapa-j3/logs/rux3f_post_v2_math_proof.py; docs/v2/etapa-j3/logs/rux3f_post_v4_audit_actor.py
- Roadmap status: 0.5.92 → 0.5.93 RUX-3F-POST DONE
- Next TODO: decisão advisor exposição Reporting vs RUX-4 (pedir DDT se âncora)
- Return to advisor: docs/v2/etapa-j3/J3_RUX_3F_POST_ADVISOR_HANDOFF.md
```
