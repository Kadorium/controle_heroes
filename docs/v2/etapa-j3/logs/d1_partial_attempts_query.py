"""D1 — inventário de attempts PARTIAL/UNKNOWN nos dois bancos (evidência RUX-2R-b)."""
from __future__ import annotations

from sqlalchemy import create_engine, text

DBS = {
    "epic_v2": "postgresql://postgres@localhost:5433/epic_v2",
    "epic_v2_test": "postgresql://postgres@localhost:5433/epic_v2_test",
}

ATTEMPT_STATUS = "SELECT status, count(1) FROM ingestion_commit_attempts GROUP BY status ORDER BY status"
NON_TERMINAL = (
    "SELECT id, document_id, operation_key, status, created_at "
    "FROM ingestion_commit_attempts "
    "WHERE status IN ('PARTIAL', 'UNKNOWN') ORDER BY id"
)
OP_STATUS = (
    "SELECT status, count(1) FROM ingestion_commit_operations GROUP BY status ORDER BY status"
)


def main() -> None:
    for name, url in DBS.items():
        print(f"=== {name} ===")
        try:
            eng = create_engine(url)
            with eng.connect() as conn:
                print("attempts_by_status:", conn.execute(text(ATTEMPT_STATUS)).fetchall())
                rows = conn.execute(text(NON_TERMINAL)).fetchall()
                print("partial_or_unknown_count:", len(rows))
                for r in rows:
                    print("  ", tuple(r))
                try:
                    print("ops_by_status:", conn.execute(text(OP_STATUS)).fetchall())
                except Exception as exc:
                    print("ops_by_status: n/a", exc.__class__.__name__)
        except Exception as exc:
            print("ERRO:", exc.__class__.__name__, str(exc)[:200])


if __name__ == "__main__":
    main()
