# Documentação Epic Controle

## Autoridade por assunto

| Assunto | Canônico |
|---|---|
| Comportamento, produto, arquitetura-alvo, telas, fluxos, aceite | [`docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md`](v2/BLUEPRINT_SISTEMA_EPIC_V2.md) |
| Fases, status, gates, ADRs, evidências, bloqueios | [`ROADMAP_V2_EPIC.md`](../ROADMAP_V2_EPIC.md) (raiz do repo) |
| Índice e autoridade documental | **Este arquivo** |
| Roteamento V1 vs V2 + política Git | [`.cursor/rules/epic-project-router.mdc`](../.cursor/rules/epic-project-router.mdc) (global) |
| Método em código/docs V2 | [`.cursor/rules/epic-v2-architecture.mdc`](../.cursor/rules/epic-v2-architecture.mdc) |
| Método legado MVP V1 | [`.cursor/rules/importacao-epic-indice.mdc`](../.cursor/rules/importacao-epic-indice.mdc) + docs em `docs/v1/` |
| Histórico / as-built V1 | [`docs/v1/README.md`](v1/README.md) |
| Validação em execução | Código real (inspecionar) |

**Canônicos ativos V2:** Blueprint V2 · Roadmap V2 · este README.  
**Checklist V1 nunca é DoD da V2.**

Precedência operacional **dentro** do Roadmap (anti-regressão documental): ver cabeçalho + bloco “Precedência interna” em [`ROADMAP_V2_EPIC.md`](../ROADMAP_V2_EPIC.md) — Blueprint / §M.1 / §J / §L / §N prevalecem sobre A–E/B histórico.

## Layout documental (pós-Fundação)

```text
docs/
├── README.md                          ← este índice
├── v1/
│   ├── README.md
│   ├── BLUEPRINT_SISTEMA_EPIC_V1.md   ← histórico
│   ├── DOCUMENTACAO_TECNICA_EPIC_V1.md
│   ├── CHECKLIST_MVP_IMPORTACAO_EPIC_V1.md
│   ├── CURSOR_RULES_IMPORTACAO_EPIC.md
│   └── archive/                       ← entregas, guias, relatórios, prompts
└── v2/
    └── BLUEPRINT_SISTEMA_EPIC_V2.md   ← canônico V2
```

Código: `v1/` (legado) · `v2/` (novo) · `ROADMAP_V2_EPIC.md` na raiz.

## O que não misturar

| Colocar no Blueprint | Colocar no Roadmap |
|---|---|
| Destino funcional e arquitetural | Status, gates, evidências |
| Critérios de aceite | Resultados de testes/comandos |
| Grafo de dependências | Checkpoint Git, plano de move |
| Gatilhos de manutenibilidade | Changelog operacional |

## Protocolo DOC_DELTA (sincronização com advisor)

Toda entrega futura do Cursor que toque a trilha V2 deve **terminar** com o bloco abaixo (preenchido). Objetivo: evitar uploads desnecessários ao advisor.

```text
DOC_DELTA
- Blueprint: NONE | UPDATED
- Roadmap: NONE | UPDATED
- Cursor Rules: NONE | UPDATED

MATERIALIDADE
- NONE
- EXECUTION_ONLY
- PHASE_CHANGE
- ARCHITECTURE_CHANGE

UPLOAD_RECOMMENDATION
- NO_UPLOAD
- UPLOAD_ROADMAP
- UPLOAD_BLUEPRINT_AND_ROADMAP
- UPLOAD_RULES
```

### Critérios de materialidade → upload

| Situação | MATERIALIDADE típica | UPLOAD_RECOMMENDATION |
|---|---|---|
| Só código/teste, sem mudança de fase nem de docs canônicos | `EXECUTION_ONLY` (ou `NONE` se trivial) | `NO_UPLOAD` |
| Encerramento ou mudança de fase / status em §J·§L·§N | `PHASE_CHANGE` | `UPLOAD_ROADMAP` |
| Mudança de módulo, ownership, cardinalidade, fluxo, estado ou aceite | `ARCHITECTURE_CHANGE` | `UPLOAD_BLUEPRINT_AND_ROADMAP` |
| Mudança no método de trabalho (rules, gates de processo, DOC_DELTA) | — | `UPLOAD_RULES` (e Roadmap/README se o protocolo/status mudou) |

Notas:

- Atualizar o **cabeçalho de sincronização** do Roadmap quando a entrega for `PHASE_CHANGE` ou `ARCHITECTURE_CHANGE`.
- `UPDATED` no DOC_DELTA só se o arquivo correspondente foi de fato editado na entrega.
- Se Blueprint e Rules mudarem na mesma entrega, combinar recomendações (upload Blueprint+Roadmap **e** Rules).
