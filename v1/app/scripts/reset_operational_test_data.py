"""CLI: reset operacional de dados demo/teste."""

import argparse
import sys

from app.database import SessionLocal
from app.services.reset_operational_data import RESET_ENV_VAR, reset_operational_test_data


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset dados operacionais Epic (dev/test)")
    parser.add_argument("--skip-backup", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = reset_operational_test_data(db, skip_backup=args.skip_backup)
        print("Reset operacional concluído:")
        for k, v in result.items():
            print(f"  {k}: {v}")
        return 0
    except RuntimeError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        print(f"Execute com: $env:{RESET_ENV_VAR}=1", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
