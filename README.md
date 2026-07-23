# Epic Controle

Monólito modular de controle de importações (Epic / Heroes).

## Layout

| Caminho | Conteúdo |
|---|---|
| [`docs/`](docs/README.md) | Documentação (`docs/v2` Blueprint canônico; `docs/v1` histórico arquivado) |
| [`ROADMAP_V2_EPIC.md`](ROADMAP_V2_EPIC.md) | Execução V2 (fases, gates, evidências) |
| [`v1/`](v1/) | Sistema legado executável (consulta + equivalência) |
| `v2/` | Sistema novo (criado na Fundação) |

## Portas e bancos

| App | Porta | Banco |
|---|---|---|
| V1 | 8080 | `epic_importacao` |
| V2 | 8081 | `epic_v2` |

## Como subir a V1

```bat
cd v1
install.bat
start_server.bat
```

## Cursor Rules

- Global: `.cursor/rules/epic-project-router.mdc`
- V1: `.cursor/rules/importacao-epic-indice.mdc`
- V2: `.cursor/rules/epic-v2-architecture.mdc`
