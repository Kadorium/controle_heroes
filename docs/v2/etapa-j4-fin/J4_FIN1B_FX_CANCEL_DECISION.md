# J4-FIN FIN-1B — Decisão FxExecution no cancel (pré-código)

| Campo | Valor |
|---|---|
| Data | 2026-08-11 |
| Preferência advisor | CANCELAR FX, não apagar |
| Migration | **NÃO** nesta fatia |

## Evidência

`FxExecution` (`fx_executions`) **não tem** `status` / `cancelled_at` — só amounts, rate, dates, payment_id ([`fx_models.py`](../../../v2/app/treasury/fx_models.py)). Cancelamento tipado exigiria Alembic **023** (fora do mandato sem PARE+autorização).

## Decisão (sem migration)

1. **Não apagar** FxExecution (trilha financeira preservada).
2. **Não criar** coluna status agora.
3. **Ciclo de vida ativo** = join com `Payment.status = REGISTERED`. Consolidados/listas de adiantamento já fazem isso.
4. No `cancel_payment` (único caminho — painel e `/payments/{id}`): após CANCELLED do Payment, emitir Audit `fx.realized.void_by_payment_cancel` por execução, com EUR/BRL/taxa/pedido/motivo. A execução **não fica órfã de sentido**: permanece histórica, vinculada ao pagamento cancelado, e fora de qualquer consolidado ativo.
5. Edit in place: **não** implementar (mandato).

Se o advisor quiser `status` explícito em FX depois → migration autorizada em fatia própria.
