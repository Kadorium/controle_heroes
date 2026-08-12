from sqlalchemy import create_engine, text

e = create_engine("postgresql://postgres@localhost:5433/epic_v2")
with e.connect() as c:
    print(
        c.execute(
            text(
                "select min(observed_at::date), max(observed_at::date), "
                "count(distinct observed_at::date) from fx_market_quotes"
            )
        ).fetchone()
    )
    print(
        c.execute(
            text(
                "select observed_at::date as d, count(1) as n "
                "from fx_market_quotes group by 1 order by 1 desc limit 20"
            )
        ).fetchall()
    )
