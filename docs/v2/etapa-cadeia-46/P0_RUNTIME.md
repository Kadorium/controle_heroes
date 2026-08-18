# P0 — Campanha elos 4–6

Data: 2026-08-13

## Runtime

| Lane | URL | DB | Cookie | Alembic | Health |
|---|---|---|---|---|---|
| Operação | `http://127.0.0.1:8081` | `epic_v2` | `epic_v2_session` | 025 | Operação — **não destrutivo** nesta campanha |
| Teste | `http://127.0.0.1:8082` | `epic_v2_test` | `epic_v2_test_session` | 025 | `runtime_lane=Teste`, `schema_ok=true` |

`epic_v2_test` estava só com `alembic_version=021` e **sem tabelas** (pytest `drop_all` de sessão anterior). Schema público recriado **somente** em `epic_v2_test` e `alembic upgrade head` → **025**. `epic_v2` **não** foi resetado.

Anexos/quarentena da lane Teste: `v2/data/attachments_test`, `v2/data/quarantine_test`.

Pytest contra `epic_v2_test` **apaga** o schema (`conftest` drop_all). Walks UI e pytest não podem partilhar a mesma janela sem re-bootstrap.

## Amostra confirmada: corpus 328

**Hipótese P0: CONFIRMADA** como fio 4–6. 244 não tem Packing List. 202 fica como robustez C6C (7 SKUs, ~centenas de cartons).

| Documento | Papel | Honestidade |
|---|---|---|
| `Fattura_328.pdf` | Elo 3/4/5 | **PDF real** — 1 linha SKU `8057628953593` qty 50 @ 106,66; total 5333,00; scadenze 1250 (2026-05-18) + 4083 (2026-07-31); IBAN da fatura nulo |
| `PackingList_328.pdf` | Elo 6 | **PDF real** — 5 cartons × 10 = 50; NCM `95069900`; desc RACCHETTA BT 2026 STARLIGHT; **não** 4819 |
| Ordine 328 | — | **Ausente no corpus** |
| Order + Product + Supplier | Elo 1 (prep) | **Mock via UI/API** — não fingir que o pedido veio do PDF |
| Adiantamento / saldo | Elo 2/4 | **Mock operacional** na lane Teste (valor 1250 alinhado à 1.ª scadenza do PDF) |

## Adapter PL Detail — gap confirmado (C6)

`extract()` lia cartons no texto **default** do pypdf (colunas estilhaçadas) → `carton_rows=[]` e issue `NO_CARTON_ROWS`. No modo **layout**, as 5 linhas de carton 328 estão numa linha só. C6A deve parsear layout (fallback default). Grouped 328 **não** vira SoT (DEC-C6-DETAIL-SOT).

## DECs C6 (ratificadas na autorização)

IDENTITY · INVOICE-OPTIONAL · LINE-MATCH · COMMITMENT · PLANNED-ONLY · DETAIL-SOT · SHIPMENT-TARGET (inclui idempotência ao nível do documento IR).
