# Manifestos E2E

Uma spec por linha. `#` e linhas vazias são ignorados. Cada `npm run e2e:<suite>` faz **prepare fresco** (reset `epic_v2_test`).

## Isolamento

`cat-pim` importa 92 produtos no mesmo banco da suíte. `rux-3b-2b` exige **catálogo vazio**. Nunca listar os dois no mesmo `E2E_SPECS`.

| Suite | Specs | Nota |
|---|---|---|
| `rux-3b-2b` | jornada Ordine catálogo vazio | Sozinha; prepare fresco |
| `cat-pim` | catálogo 92 | Polui o catálogo |
| `j3-uiv` | aceite ingestão UI humana | Não exigir painel IR no Ordine |
| `logistics-ui-journey` | jornada logística por cliques | Precisa SKU+descrição no criar pedido |
| `rbac` | papéis comprador/aduana/estoque | Usuários só no prepare de teste |
| `elo-10` | encerrar/reabrir pedido | Após Onda A (modal não abre vazio) |
| `ordine-order-ui` | Ordine PDF na tela de pedido | Prepare fresco; não misturar com cat-pim |
| `j8-order-billing` | inc1/inc2/inc3 UI (SC-15/01/02/03) | Prepare fresco; CTA `orders-new-cta` |
| `j8-close` | SC-08 fatura emitida + SC-17 tolerância provisória | Prepare fresco; SC-10 na suíte `j5` |
| `j5-rec` | compromisso → vincular SKU → estoque | Prepare fresco; SKU ≠ EAN / I.V.* |
| `ing-fam` | Fattura PDF na comercial + planilha no novo pedido | Prepare fresco; SKU ≠ EAN |
| `b0` | picker residual da fatura digitada na comercial | Prepare fresco; SKU ≠ EAN |
| `prof-stable` | j7, j6, j5, i9-0, inc-6, funding, mdm | Sem cat-pim + rux juntos |

`npm run e2e:j8` — aceite J#8: suítes isoladas em sequência (cat-pim isolado; `j8-close` por último; rux ≠ cat-pim).

## Gate das 5 specs (Onda B)

Rodar **nas suítes certas**, não num run combinado:

1. `inc4-fx` + `inc5-ap-cockpit` — `horizon-a` (ou isoladas)
2. `j4-logistics-ui-journey` — `logistics-ui-journey`
3. `j3-uiv-acceptance` — `j3-uiv`
4. `rux-3b-2b-ordine-journey` — `rux-3b-2b` (nunca com `cat-pim`)
