"""RUX-3F-POST V4 — read-only audit actor for Order 31 confirm."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

root = Path(__file__).resolve().parents[4]  # Controle/
load_dotenv(root / "v2" / ".env")
load_dotenv(root / ".env")

url = os.environ.get("DATABASE_URL") or "postgresql://postgres:postgres@127.0.0.1:5433/epic_v2"
# force psycopg2 driver
if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
elif url.startswith("postgresql+psycopg://"):
    url = url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)

print("db=", url.split("@")[-1])
eng = create_engine(url)
with eng.connect() as c:
    rows = c.execute(
        text(
            """
            SELECT id, actor_id, action, reason_code, created_at, details, entity_type, entity_id
            FROM audit_log
            WHERE id = 913
               OR (entity_type = 'order' AND entity_id = '31' AND action = 'confirm')
            ORDER BY id
            """
        )
    ).mappings().all()
    print("audit_rows=", len(rows))
    for r in rows:
        print(dict(r))
        aid = str(r["actor_id"])
        u = c.execute(
            text("SELECT id, email, name, role FROM users WHERE cast(id as text) = :a"),
            {"a": aid},
        ).mappings().first()
        print("resolved_user=", dict(u) if u else None)
