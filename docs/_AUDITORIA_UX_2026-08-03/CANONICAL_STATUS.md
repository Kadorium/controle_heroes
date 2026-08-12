# Status dos arquivos canônicos

Verificado via `git log --oneline -20`, `git log -1 --format=%ai -- <arquivo>` (para arquivos versionados) e `stat` (mtime de filesystem, para arquivos ainda não commitados).

## `git log --oneline -20`

```
5ccdc5b Update ROADMAP and documentation for Inc-5 completion and Inc-6 planning
f9a83ed Remove deprecated files and update .gitignore for improved project structure
008fb49 Enhance importation and product management features
48510e7 Enhance financial and importation features
aa319a6 Enhance product catalog and importation features
0636d72 Enhance product management and importation functionality
8224a96 Add tests for BRL settlement conversion and invoice handling
c549dec Implement entreposto movement tracking and enhance financial APIs
a402f45 Enhance importation models and APIs with new fields and functionality
ca7ec86 Enhance Heroes import functionality with XLSX support and currency normalization
592d458 Initial commit: MVP Controle Importação Epic (Heroes)
```
(Apenas 11 commits existem no repositório — a lista completa tem menos de 20 entradas.)

## Tabela de status

| Canônico | Caminho real encontrado | Última modificação | Linhas | Status |
|---|---|---|---|---|
| BLUEPRINT_SISTEMA_EPIC_V2.md | `docs/v2/BLUEPRINT_SISTEMA_EPIC_V2.md` | 2026-08-03 (working tree, `git status` mostra `M`; último commit em 2026-07-28) | 1449 | Modificado, não commitado — em edição ativa |
| ROADMAP_V2_EPIC.md | `ROADMAP_V2_EPIC.md` | 2026-08-03 (working tree; último commit 2026-07-28) | 231 | Modificado, não commitado — em edição ativa |
| BLUEPRINT_UI_UX_EPIC_v3.md | `docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md` | 2026-08-03 (working tree; último commit 2026-07-28) | 2198 | Modificado, não commitado — em edição ativa |
| CURSOR_RULES_IMPORTACAO_EPIC.md | `docs/v1/CURSOR_RULES_IMPORTACAO_EPIC.md` | 2026-07-31 (mtime); último commit 2026-07-23 | 559 | Modificado, não commitado (mtime mais recente que o commit) |
| docs/v2/epic-v2.mdc | **Não encontrado nesse caminho.** Existe em `.cursor/rules/epic-v2.mdc` | mtime 2026-07-31 14:42 | 63 | Encontrado em local diferente do esperado; **arquivo novo, nunca commitado** (`git status` mostra `??`) |
| HANDOFF_UI_UX_EPIC_V2.md | **Não encontrado na raiz.** Existe em `docs/v2/blueprint UIUX/HANDOFF_UI_UX_EPIC_V2.md` | mtime 2026-07-31 14:42 | 658 | Encontrado em local diferente do esperado; **arquivo novo, nunca commitado** (`git status` mostra `??`) |

## Observações

- Os três blueprints principais (Sistema V2, UI/UX v3, Roadmap) foram editados **hoje (2026-08-03)**, no mesmo dia da auditoria — são os documentos mais "quentes" do projeto no momento.
- `epic-v2.mdc` e `HANDOFF_UI_UX_EPIC_V2.md` não existem nos caminhos pedidos pelo prompt original; foram localizados por busca (`find -iname`). Ambos são arquivos **untracked** (nunca commitados no git), criados em 2026-07-31 — provavelmente artefatos de trabalho em andamento que ainda não foram integrados ao controle de versão.
- O `git status` no início desta sessão também mostra como **deletados** (`D`, ainda não commitado) dois arquivos antigos de regras: `.cursor/rules/epic-project-router.mdc` e `.cursor/rules/epic-v2-architecture.mdc` — sugerindo uma reorganização em andamento das regras `.mdc` (possivelmente consolidando-as em `.cursor/rules/epic-v2.mdc`, que é justamente o arquivo novo/untracked acima).
- Nenhum dos 6 canônicos está "desatualizado" no sentido de abandonado — todos têm atividade recente (últimos 3-13 dias a partir da data da auditoria).
