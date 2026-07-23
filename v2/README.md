# Epic Controle V2 — Fundação

Porta padrão: **8081**. Banco: **epic_v2** (teste: **epic_v2_test**).

## Backend

```bat
cd v2
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8081
```

## Frontend

```bat
cd v2\frontend
npm install
npm run generate:api
npm run build
```

Scripts úteis: `npm run check:api-drift`.

Módulos nesta fase: Foundation, Identity, Audit, Documents (sem stubs de domínio futuro).
