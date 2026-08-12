from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    cols = [
        r[0]
        for r in c.execute(
            text(
                "select column_name from information_schema.columns "
                "where table_name='audit_log' order by ordinal_position"
            )
        )
    ]
    print("COLS", cols)
    # flexible query based on cols
    rows = c.execute(
        text(
            "select * from audit_log where entity_id::text = '31' "
            "or cast(details as text) ilike '%589%' "
            "or cast(details as text) ilike '%confirm%' "
            "order by id desc limit 40"
        )
    ).mappings().all()
    for r in rows:
        print(dict(r))
