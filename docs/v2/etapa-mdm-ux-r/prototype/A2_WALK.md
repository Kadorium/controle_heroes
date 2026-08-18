# Percurso A2 — Abri / Vi / Cliquei / Resultado

Proto: `http://127.0.0.1:8765/` · 2026-08-18. Fonte bruta: [`A2_WALK.json`](A2_WALK.json).

1. **Busca** — Abri `#/catalog/products`. Vi busca dominante sem botão Buscar, KPIs rotulados, tabela. Digitei `STARLIGHT` (debounce 280ms). Resultado: 6 resultados · página 1 de 1.
2. **Quick filter** — Abri lista sem filtro. Vi chip Dados incompletos. Cliquei o quick filter. Resultado: KPI ativo + chip removível + 91 resultados · página 1 de 5.
3. **Mais filtros** — Vi botão Mais filtros. Cliquei. Resultado: facets Tamanho / Cor / Origem só com valores.
4. **Remover chip** — Vi chip Dados incompletos. Cliquei ×. Resultado: filtro saiu; 100 resultados · página 1 de 5.
5. **Paginação** — Vi Próxima. Cliquei. Resultado: 100 resultados · página 2 de 5.
6. **Ordenação** — Vi select Ordenar. Selecionei SKU. Resultado: lista reordenada; offset resetado a 0.
7. **Abrir ficha** — Filtrei `WASH BAG`. Cliquei a linha inteira. Resultado: leitura; H1 = descrição humana; SKU secundário; badge Ativo.
8. **Voltar** — Cliquei Voltar à lista. Resultado: `#/catalog/products?q=WASH+BAG&row=97` (query/contexto preservados).
9. **Leitura → edição** — Abri a ficha. Vi Editar explícito. Cliquei Editar. Resultado: seções verticais; SKU readonly.
10. **Create mínimo** — Abri `#/catalog/products/new`. Vi SKU + descrição + Criar. Cliquei Criar. Resultado: ficha na sessão; notice “nada gravado em epic_v2”.
