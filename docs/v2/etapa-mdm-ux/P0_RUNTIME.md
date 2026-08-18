# P0 — Campanha MDM-UX (fechada)

Data: 2026-08-18

| Lane | URL | DB | Cookie | Alembic | Uso |
|---|---|---|---|---|---|
| Operação | `http://127.0.0.1:8081` | `epic_v2` | `epic_v2_session` | **026** (schema nullable; sem reset) | Inspeção. Pedidos 589/id31 e TESTE-CICLO-001/id34 **intocados** |
| Teste | `http://127.0.0.1:8082` | `epic_v2_test` | `epic_v2_test_session` | **026** | Única lane mutável; walk MDM-CF |
| UI teste | Vite `dev:test` (`http://localhost:5174` → `:8082`) | — | cookie da lane teste | — | Walk MDM-CF |

Pytest contra `epic_v2_test` **apaga** o schema (`conftest` drop_all). Depois do pytest full desta campanha o schema ficou em 025 **sem** tabelas; rebuild obrigatório: [`mdm_rebuild_test_schema.py`](mdm_rebuild_test_schema.py) (DROP SCHEMA public **somente** `epic_v2_test` → upgrade 001…026 + seed admin/DOMESTIC-MAIN). Massa >50 **só** em `epic_v2_test`: [`mdm_cf_seed.py`](mdm_cf_seed.py).

CSV de catálogo = **FUTURO**.
