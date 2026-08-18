# P0 — Campanha Elo 8

Data: 2026-08-17

## Runtime (E8-0)

| Lane | URL | DB | Cookie | Alembic | Uso nesta campanha |
|---|---|---|---|---|---|
| Operação | `http://127.0.0.1:8081` | `epic_v2` | `epic_v2_session` | 025 | **Somente inspeção.** Pedidos 589/id31 e TESTE-CICLO-001/id34 intocados |
| Teste | `http://127.0.0.1:8082` | `epic_v2_test` | `epic_v2_test_session` | 025 | Única lane mutável |
| UI teste | Vite `dev:test` (típico `:5174` → API `:8082`) | — | cookie da lane teste | — | Walk E8-5 |

Git: `main` @ `3b10deb`. Alembic script head = `EXPECTED_ALEMBIC_REVISION` = **025**. Sem revision 026.

Health 8082: `app_env=test`, `logical_database=epic_v2_test`, `schema_ok=true`.  
Health 8081: `app_env=development`, `logical_database=epic_v2`, `schema_ok=true` — **nenhum reset**.

Pytest contra `epic_v2_test` **apaga** o schema (`conftest` drop_all). Walk UI **depois** do pytest full (E8-4) e re-bootstrap da 202.

Mestre: **DONE** após E8-5 PASS e E8-6 (Roadmap 0.5.121 / Blueprint 0.2.24). DECs PATH/BIND/COVERAGE/ARRIVAL/DOC/NAT-REVERSE=B/STUBS vigentes.

Walk E8-5: UI `http://localhost:5174` (Vite `dev:test`; escuta IPv6 — usar `localhost`, não `127.0.0.1`).

E8-FINAL-VERIFY (2026-08-17): suite + W1–W8 no código final + história 202 PDFs → estoque na mesma lane. `epic_v2` intocado.
