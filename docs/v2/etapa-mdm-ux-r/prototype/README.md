# Protótipo MDM-UX-R

Isolado de produção. Não é importado pelo frontend V2. Sem backend, sem `epic_v2`.

## Servir

Na pasta deste diretório:

```text
python -m http.server 8765
```

Abrir `http://127.0.0.1:8765/`

## Fixture

`fixtures/catalog-visual.json` — 92 SKUs do CSV V1 (`heroes_produtos_epic_import_final.csv`) como **fixture visual read-only**, mais 8 linhas `source=proto-fake` (B5, incompleto, inativo, L-006 rico).

Isto **não** é migração V1→V2 nem requisito de CSV de catálogo.

## IA no proto (não no AppShell real)

Catálogo → Produtos. Fornecedores e Prestadores fora do rail. Fornecedor via `⋯`. Prestadores via CTA em Embarques.
