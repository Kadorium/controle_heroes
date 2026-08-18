# P0 — Campanha Elo 7

Data: 2026-08-14

## Runtime

| Lane | URL | DB | Cookie | Alembic | Uso nesta campanha |
|---|---|---|---|---|---|
| Operação | `http://127.0.0.1:8081` | `epic_v2` | `epic_v2_session` | 025 | **Somente inspeção.** Pedidos 589/id31 e TESTE-CICLO-001/id34 intocados |
| Teste | `http://127.0.0.1:8082` | `epic_v2_test` | `epic_v2_test_session` | 025 | Única lane mutável |

Pytest contra `epic_v2_test` **apaga** o schema (`conftest` drop_all). Walk UI e pytest não partilham a mesma janela sem re-bootstrap.

## Hipótese de história única — investigada no corpus inteiro

Não limitar a “Numerário 328”. Único PDF de Solicitação de Numerário no corpus V2: `corpus_202/Solicitacao_Numerario.pdf`.

| Família | Fattura | PL Detail | PL Grouped | Doganale | Print | Numerário | Ordine |
|---|---|---|---|---|---|---|---|
| **202** | sim | sim | sim | sim | sim | **sim** | ausente |
| **328** | sim | sim | sim | sim | sim | **não** | ausente |
| 181 | sim (acconti) | sim | sim | sim | sim | não | ausente |
| 244 | sim | não | não | sim | não | não | ausente |
| 245 | sim | não | não | sim | não | não | ausente |
| 332 | sim | não | não | sim | não | não | ausente |
| 589 | não | não | não | não | não | não | sim |

**Conclusão:** a única família comercial/aduaneira real capaz de Shipment → chegada → Doganale/declaração → fatos tributários documentais → nacionalização, **num mesmo conjunto de PDFs**, é a **202**.

A 328 continua a melhor história 1→6 já aceita (1 SKU, qty 50), mas **não contém tributos BR**. Inventar II/IPI/PIS/COFINS/AFRMM/ICMS a partir da Doganale 328 é proibido.

O Numerário 202 cita faturas `181/202/203/244/245/246` (nível DUIMP, não só a fatura 202). Os tributos são fatos **desse PDF**, não da Fattura comercial 202 isolada. A história única usa a família 202 como espinha e registra os tributos no mesmo ImportProcess, com essa honestidade.

## Sinais — Fattura Doganale 328

PDF: `v2/tests/fixtures/ingestion/corpus_328/FatturaDoganale_328.pdf` (extract real, adapter `fattura_doganale_v1`).

| Campo | Valor extraído | Honestidade |
|---|---|---|
| Nº documento | 328 | PDF real |
| Total | 5333.00 EUR | PDF real |
| Linhas | 1 | PDF real |
| Qty | 50 | PDF real |
| NCM | `95069900` | PDF real |
| Descrição | RACCHETTA (BT 2026 STARLIGHT) | PDF real |
| Origem | texto “Italy” (não ISO-2) | **não** gravar como `IT` |
| II/IPI/PIS/COFINS/AFRMM/ICMS | **ausentes** | não derivar |

## Sinais — família 202 (história única candidata)

### Fattura Doganale 202

PDF: `corpus_202/FatturaDoganale_202.pdf`

| Campo | Valor extraído |
|---|---|
| Nº | 202 |
| Total | 30188.00 EUR |
| Linhas | 7 |
| Qty soma | 1600 |
| NCM (ex.) | `4202221000` (cabe em String(16)) |

### Solicitação de Numerário 202

PDF: `corpus_202/Solicitacao_Numerario.pdf` · payee Bechtrans → EPIC · refs INV. 181/202/203/244/245/246

| Code | Amount BRL | Fonte |
|---|---|---|
| AFRMM | 2000.00 | PDF real |
| ICMS | 556000.00 | PDF real |
| II | 343800.00 | PDF real |
| IPI | 253500.00 | PDF real |
| PIS | 37700.00 | PDF real |
| COFINS | 167900.00 | PDF real |
| SISCOMEX | 223.64 | PDF real |
| Total declarado | 1425554.64 | PDF real |
| FOB | EUR 288195.20 | PDF real (nível DUIMP) |

Despesas (frete int., armazenagem, honorários, …) no mesmo PDF — `CustomsExpenseLine`, não tributo.

## Mock operacional autorizado (não é evidência documental)

Order, Product, Supplier, Shipment auxiliar, DUIMP digitado (L-007), múltiplos ShipmentItems para gate quantitativo. Rotulados como ensaio.

## DEC-E7-ARRIVAL-GATE (dívida — não implementar)

O domínio Customs permite nacionalização sem exigir Shipment ARRIVED. A campanha demonstra ARRIVED na jornada Logistics; **não** cria a trava. Avaliar futuramente se chegada física/documental deve ser precondição de nacionalização.
