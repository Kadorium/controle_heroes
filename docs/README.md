# Documentação Epic Controle

## Autoridade por assunto

| Assunto | Documento / autoridade |
|---|---|
| Entidades, cardinalidades, ownership, regras de domínio, arquitetura-alvo, fluxos e aceite de domínio | [`docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md`](v2/BLUEPRINT_SISTEMA_EPIC_V2.md) — **canônico** |
| Fases, status, gates, ADRs, evidências, bloqueios | [`ROADMAP_V2_EPIC.md`](../ROADMAP_V2_EPIC.md) (raiz do repo) — **canônico** |
| Arquitetura de informação, interação, design system e critérios de UX | [`docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md`](v2/blueprint%20UIUX/BLUEPRINT_UI_UX_EPIC_v3.md) — **candidato v3.7 não canônico**; mockups [`mockups/`](v2/blueprint%20UIUX/mockups/) **MCK v1.1** (Etapa 6 DONE) |
| Índice e autoridade documental | **Este arquivo** — **canônico** (índice) |
| Roteamento V1 vs V2 + política Git | [`.cursor/rules/epic-project-router.mdc`](../.cursor/rules/epic-project-router.mdc) (global) |
| Método em código/docs V2 | [`.cursor/rules/epic-v2-architecture.mdc`](../.cursor/rules/epic-v2-architecture.mdc) |
| Método legado MVP V1 | [`.cursor/rules/importacao-epic-indice.mdc`](../.cursor/rules/importacao-epic-indice.mdc) + docs em `docs/v1/` |
| Histórico / as-built V1 | [`docs/v1/README.md`](v1/README.md) |
| Validação em execução / evidência na investigação | Código real (inspecionar) |
| Benchmark de mercado | Evidência consultiva, sem autoridade (corpus em `docs/v2/blueprint UIUX/`) |

**Canônicos ativos V2:** Blueprint do Sistema · Roadmap V2 · este README.

**Candidato documental em revisão:** Blueprint UI/UX EPIC [v3.7](v2/blueprint%20UIUX/BLUEPRINT_UI_UX_EPIC_v3.md). Mockups prioritários: [MCK v1.1](v2/blueprint%20UIUX/mockups/) (Etapa 6 DONE; E6-B pendente confirmação externa). Não integra o conjunto canônico até promoção explícita.

**Checklist V1 nunca é DoD da V2.**

### Regra de conflito

- Domínio, entidades, cardinalidades, ownership e invariantes → Blueprint do Sistema.
- Fases, status, gates e evidências → Roadmap.
- Arquitetura de informação, interação e design system → Blueprint UI/UX **após aprovação**.
- Enquanto candidato, divergências do UI/UX devem ser registradas e **não** alteram os canônicos.
- Código real prevalece como evidência durante investigação; divergências documentais resolvem-se nos documentos responsáveis.

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
    ├── BLUEPRINT_SISTEMA_EPIC_V2.md   ← canônico V2
    └── blueprint UIUX/
        ├── BLUEPRINT_UI_UX_EPIC_v3.md   ← candidato v3.7 não canônico
        └── mockups/                    ← MCK v1.1 vigente (v0.1–v1.0 histórico)

```

Código: `v1/` (legado) · `v2/` (novo) · `ROADMAP_V2_EPIC.md` na raiz.

## O que não misturar

| Colocar no Blueprint do Sistema | Colocar no Roadmap | Colocar no Blueprint UI/UX (quando aprovado) |
|---|---|---|
| Destino funcional e arquitetural | Status, gates, evidências | Arquitetura de informação e telas |
| Critérios de aceite de domínio | Resultados de testes/comandos | Interação, design system, aceite de UX |
| Grafo de dependências / ownership | Checkpoint Git, plano de move | Padrões de grade, a11y, navegação |
| Gatilhos de manutenibilidade de domínio | Changelog operacional | Sequência visual A0/A1 (proposta) |

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
| Atualização do candidato UI/UX e/ou índice documental sem promover canônico | `DOCUMENTATION_GOVERNANCE` | `UPLOAD_UIUX_CANDIDATE_AND_DOCS_README` |

Notas:

- Atualizar o **cabeçalho de sincronização** do Roadmap quando a entrega for `PHASE_CHANGE` ou `ARCHITECTURE_CHANGE`.
- `UPDATED` no DOC_DELTA só se o arquivo correspondente foi de fato editado na entrega.
- Se Blueprint e Rules mudarem na mesma entrega, combinar recomendações (upload Blueprint+Roadmap **e** Rules).
