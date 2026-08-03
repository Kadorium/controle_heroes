# Adaptive — Onda B piloto SCR-008

**Status:** DONE técnico — **HARD STOP** antes da Onda C  
**Data:** 2026-07-30  
**E2E:** 16 passed (Horizon A 15 + `adaptive-b-ap-pilot`) @ `epic_v2_test`:8082  

## Evidências

- Log: [`e2e-onda-b.txt`](e2e-onda-b.txt)
- Screenshots matriz: `screenshots/scr-008-ap-{1024,1280,1366,1440,1920}.png`

## Escopo entregue

- `AP_QUEUE_COLUMNS` + `OperationalTable` columns API (omit React)
- FilterBar adaptive (primary Status+Saldo; secondary Due/Moeda/Pedido/Fornecedor)
- Drawer com Pedido / Pendências / Alocado (P2/P3)
- Sem sticky col no piloto

## HARD STOP

Não migrar SCR-003 / 006 / 010 até aprovação externa explícita do piloto.
