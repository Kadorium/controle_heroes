# Piloto SCR-008 — matriz de larguras

| Largura | Shell | Modo da fila | Colunas visíveis | Filtros | Overflow H | Wrap P0 | Drawer | Veredito |
|---|---|---|---|---|---|---|---|---|
| 1024 | rail 56px | standard | Vencimento, Fornecedor, Fatura, Saldo, Status, Pedido, Valor | secundários em linha; ativo Status visível | sim (scroll) | não | acessível (Alocado/Pendências/Pedido) | PASS |
| 1280 | expanded 220px | standard | Vencimento, Fornecedor, Fatura, Saldo, Status, Pedido, Valor | secundários em linha; ativo Status visível | não | não | acessível (Alocado/Pendências/Pedido) | PASS |
| 1366 | expanded 220px | standard | Vencimento, Fornecedor, Fatura, Saldo, Status, Pedido, Valor | secundários em linha; ativo Status visível | não | não | acessível (Alocado/Pendências/Pedido) | PASS |
| 1440 | expanded 220px | standard | Vencimento, Fornecedor, Fatura, Saldo, Status, Pedido, Valor | secundários em linha; ativo Status visível | não | não | acessível (Alocado/Pendências/Pedido) | PASS |
| 1920 | expanded 220px | wide | Vencimento, Fornecedor, Fatura, Saldo, Status, Pedido, Valor, Câmbio / BRL, Pendências | secundários em linha; ativo Status visível | não | não | acessível (Alocado/Pendências/Pedido) | PASS |

## Rede ao trocar largura

| Largura | Requests /api/reporting/ap* após resize |
|---|---|
| 1024 | 0 |
| 1280 | 0 |
| 1366 | 0 |
| 1440 | 0 |
| 1920 | 0 |

Gerado: 2026-07-30T21:43:59.404Z