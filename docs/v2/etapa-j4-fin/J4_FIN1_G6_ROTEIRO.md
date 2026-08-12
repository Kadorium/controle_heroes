# J4-FIN FIN-1 — Roteiro G6 (Ricardo)

Registro do **adiantamento real** do pedido **589** (id **31**) em `epic_v2` / `:8081`.

> **Ambiente limpo (2026-08-11, pós FIN-1C-FIX-1B):** painel vazio; só PDF Ordine; CONFIRMED 2 linhas. Dryrun: [`J4_FIN1_G6_DRYRUN.md`](J4_FIN1_G6_DRYRUN.md). FIX-1B: [`J4_FIN1C_FIX1B_ADVISOR_HANDOFF.md`](J4_FIN1C_FIX1B_ADVISOR_HANDOFF.md). Consolide só o que **você** registrar agora (valores reais do extrato).

## Pré-requisitos

1. Backend `:8081` com Alembic **022** (`schema_ok`).
2. Frontend dist servido — asset esperado **`index-I3tToUDS.js`** (FIX-1B).
3. Login: `admin@epic.com.br` / `admin123`.
4. Order 589 permanece **CONFIRMED** — só Payments novos.

## Passos

1. Abrir `http://127.0.0.1:8081/orders/31/commercial`.
2. Painel **Adiantamentos (crédito)** (acima de Documentos) — “Nenhum adiantamento registrado”.
3. Preencher:
   - **Valor (EUR)** — valor da transferência
   - **Taxa** *ou* **BRL do extrato** (se os dois: EUR+BRL são verdade; taxa derivada)
   - **Data do pagamento** ≠ **Data da execução de câmbio** quando forem dias diferentes
   - PDF opcional: botão **Anexar PDF de câmbio deste adiantamento** (não use Documentos do pedido)
4. Conferir preview (BRL derivado / taxa derivada) **antes** de registrar.
5. **Registrar adiantamento** — formulário deve **zerar por completo** (incluindo as duas datas).
6. Conferir consolidado (total EUR, total BRL = soma, câmbio médio).
7. Se houver 2ª parcela: repetir (campos começam vazios) — consolidado deve somar.
8. Abrir Cockpit `http://127.0.0.1:8081/orders/31` — conferir:
   - **Adiantado (crédito)** = total residual dos adiantamentos do pedido
   - **Pago (alocado)** = 0 (sem Fattura)
   - **Pagamentos deste pedido** lista só o(s) Payment(s) do 589
9. Abrir `http://127.0.0.1:8081/payables?order_id=31` → **ZERO títulos novos**.

## Se errar a taxa

No próprio painel: botão **Cancelar** na linha → confirmação (“O valor sai do consolidado”) → **motivo obrigatório** (foco inicia no Motivo) → consolidado e câmbio médio recalculam na hora. Depois registre de novo com os valores corretos. (Não há edição in-place — de propósito.)

## Proibido

Criar Invoice/Payable de compromisso; alterar linhas do 589; parse de PDF.
