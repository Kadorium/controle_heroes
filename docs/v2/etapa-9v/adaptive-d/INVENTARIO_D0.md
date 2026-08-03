# Adaptive-D — inventário D0 (campanha encerramento Horizon A)

**Data:** 2026-07-30  
**Bundle before (D0):** JS `282648` B · CSS `22735` B  
**Bundle after (D6):** JS `290180` B · CSS `24230` B — ver `EVIDENCIAS.md`

## Hipóteses

| ID | Veredito |
|---|---|
| H-CAMP-1 Sem GET /api/payables/{id} | CONFIRMADA → **FECHADA** (D0.5) |
| H-CAMP-2 get_payable no domínio | CONFIRMADA |
| H-CAMP-3 Scan listPayables+limit 100 no FX | CONFIRMADA → **FECHADA** (`getPayable`) |
| H-CAMP-4 billing:read + PayableResponse | CONFIRMADA |
| H-CAMP-5 Rota fina viável sem migration | CONFIRMADA |

## Hotspots LOC (pós-campanha)

| Arquivo | LOC approx | Nota |
|---|---|---|
| InvoiceDetailPage.tsx | ~900 | MINOR_BACKLOG split |
| FxPanels.tsx | ~437 | CQ via host |
| OrderCreatePage.tsx | ~370 | parcial create OK |
| PaymentDetailPage.tsx | ~400 | cancel + idempotency |
| OrderCockpitPage.tsx | ~300 | detail-shell RO |
| OrderDetailPage.tsx | ~260 | 409 dirty |

## E2E

- Canônico: `npm run e2e:horizon-a` (manifest `e2e/suites/horizon-a.txt`) — **18 specs**
- Inclui `adaptive-d-details.spec.ts`
- Default `npm run e2e` permanece Inc-5 apenas
