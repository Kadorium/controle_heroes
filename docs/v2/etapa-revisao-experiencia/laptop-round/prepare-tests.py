"""Idempotent laboratory preparation only: separate price tables, no SHOW mutations."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'demo-e2e'))
import runtime
from app.foundation.database import SessionLocal
from app.catalog import public as catalog
from app.catalog.models import Product
from sqlalchemy import text
with SessionLocal() as db:
    assert db.execute(text('select inet_server_port()')).scalar()==5445
    tables=[catalog.ensure_price_list(db,code=code,name=name,channel='Validação isolada',actor_id='1') for code,name in [('LAPTOP-PRICE-20261023','QA laptop · individual'),('LAPTOP-IMPORT-20261023','QA laptop · CSV')]]
    products=[db.query(Product).filter_by(sku=sku).one() for sku in ['DEMO-HR-FIERCE26','DEMO-HR-BULL-M']]
    result={'preparation':'Catalog public: isolated price tables; existing products read only','database_port':5445,'tables':[t for t in catalog.price_lists(db) if t['id'] in [x.id for x in tables]], 'products':[{'id':p.id,'sku':p.sku,'name':p.commercial_name,'unit':p.unit} for p in products]}
    db.commit()
target=runtime.lab/'laptop/fixtures.json';target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result,ensure_ascii=False))
