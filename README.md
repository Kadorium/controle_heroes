# Epic Controle

Monólito modular de controle de importações (Epic / Heroes).

## Layout

| Caminho | Conteúdo |
|---|---|
| [`docs/`](docs/README.md) | Documentação (mapa em [`docs/README.md`](docs/README.md); V2 ativa; V1 histórica) |
| [`ROADMAP_V2_EPIC.md`](ROADMAP_V2_EPIC.md) | Estado, sequência, gates e próximos passos da V2 |
| [`v1/`](v1/) | Sistema legado executável (consulta + equivalência) |
| [`v2/`](v2/) | Sistema novo (Foundation em diante) |

```text
root/
├── .cursor/rules/
├── docs/
│   ├── README.md
│   ├── v1/
│   └── v2/
│       ├── BLUEPRINT_SISTEMA_EPIC_V2.md
│       ├── blueprint UIUX/
│       ├── etapa-*/
│       └── archive/
├── ROADMAP_V2_EPIC.md
├── README.md
├── v1/
└── v2/
```

## Portas e bancos

| App | Porta | Banco |
|---|---|---|
| V1 | 8080 | `epic_importacao` |
| V2 | 8081 | `epic_v2` (teste: `epic_v2_test`) |

## Como subir a V1

```bat
cd v1
install.bat
start_server.bat
```

## Como subir a V2

Backend (detalhe em [`v2/README.md`](v2/README.md)):

```bat
cd v2
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8081
```

Frontend:

```bat
cd v2\frontend
npm install
npm run generate:api
npm run build
```

## Documentação e regras

- Mapa documental: [`docs/README.md`](docs/README.md)
- Regra operacional (sempre ativa): [`.cursor/rules/epic-v2.mdc`](.cursor/rules/epic-v2.mdc)
