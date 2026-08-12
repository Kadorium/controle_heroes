# WIP isolado — NÃO aplicar / NÃO reintegrar sem autorização

Campanhas: **RUX-3A** (Catalog 020) + artefatos **RUX-2R-b** (reextract tests / Modelo B tx tests).

Isolado **2026-08-06** por decisão Planning pós-Q3=(B).  
Árvore de execução = alembic **019**.

## Conteúdo

| Arquivo | Origem |
|---|---|
| `020_catalog_rux_identity_refs.py` | Saiu de `v2/alembic/versions/` (não descoberta por alembic) |
| `catalog_models.py.bak` | Snapshot pré-isolamento |
| `commit_commands.py.bak` / `staging_commands.py.bak` | Snapshots |
| `test_catalog_rux3a.py` | Testes RUX-3A |
| `test_ingestion_rux_reextract.py` | Testes reextract |
| `test_ingestion_rux_tx.py` | Testes Modelo B savepoints |

## Ainda no código vivo (RUX-2R-b — revisão formal)

- `commit_commands.execute_commit` — `begin_nested` / PARTIAL (não removido nesta rodada; PARE documentado)
- `staging_commands.reextract_document` — implementação; route retorna 501
