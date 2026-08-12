# RUX-3F — UI verification (Browser)

| Campo | Valor |
|---|---|
| Data | 2026-08-10 |
| Runtime | `http://127.0.0.1:8081` · `epic_v2` · asset `index-CJ3jYOR5.js` · `AMBIENTE: OPERAÇÃO` |
| Escopo | G6 checklist I1 + sanidade I2 (AP) — **sem** apagar Order 589 |
| Resultado | **PASS** (3/3) |

## Plano executado

| ID | Passo | Esperado | Resultado |
|---|---|---|---|
| T1 | `/orders/31/commercial` | Badge Confirmado; 2 Compromisso; total EUR 830.000,00; PDF anexado | **PASS** |
| T2 | Painel Faturas | Notice literal; Disponível `—`; **sem** botão Criar fatura; descrição + “compromisso” | **PASS** |
| T3 | `/payables` filtro Pedido ID `31` | `Títulos 0` — compromisso não vira AP | **PASS** |

## Literais observados (T2)

Notice:

```text
Este pedido só tem linhas de compromisso (artigos ainda sem SKU final). As faturas destes itens entram pela importação da Fattura do fornecedor — os produtos reais chegam por ali. Não é possível criar fatura manual aqui.
```

Tabela:

```text
racchette 2027 GRAFICATE · compromisso	14.600	0	—
racchette 2027 NON GRAFICATE · compromisso	2.000	0	—
Nenhuma fatura
```

`createBtn` no DOM: **false**.

## Screenshots

- [`screenshots/rux3f/rux3f-uiv-t2-faturas-panel.png`](screenshots/rux3f/rux3f-uiv-t2-faturas-panel.png)
- [`screenshots/rux3f/rux3f-uiv-t3-payables-order31-empty.png`](screenshots/rux3f/rux3f-uiv-t3-payables-order31-empty.png)

## Nota

Isto **não** substitui o aceite G6 do Ricardo; é verificação automatizada Browser do agente sobre o runtime operacional.
