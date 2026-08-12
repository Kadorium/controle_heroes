from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print("alembic", c.execute(text("select version_num from alembic_version")).scalar())
    print(
        "has_order_id",
        c.execute(
            text(
                "select count(1) from information_schema.columns "
                "where table_name='payments' and column_name='order_id'"
            )
        ).scalar(),
    )
    print("order31", c.execute(text("select id, code, status from orders where id=31")).fetchone())
