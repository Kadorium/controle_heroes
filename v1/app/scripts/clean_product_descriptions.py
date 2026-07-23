"""Limpa nomes de produtos já importados — remove # e separa ano explícito."""

from app.database import SessionLocal
from app.services.product_name_normalize import normalize_existing_products


def main() -> None:
    db = SessionLocal()
    try:
        result = normalize_existing_products(db)
        print(
            f"Produtos verificados: {result['scanned']}; "
            f"atualizados: {result['updated']}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
