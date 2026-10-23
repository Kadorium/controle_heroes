"""Explicit scale fixture on the verified unit cluster, never the demo/candidate."""
import os,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[4];lab=repo.parent/'audit-lab/stock-executive-20261023'
os.environ.update(APP_ENV='test',DATABASE_URL='postgresql://postgres@127.0.0.1:5446/epic_v2_test',ATTACHMENTS_PATH=str(lab/'scale-storage/attachments'),QUARANTINE_PATH=str(lab/'scale-storage/quarantine'),LOGS_PATH=str(lab/'scale-logs'),FRONTEND_DIST_PATH=str(repo/'v2/frontend/dist'),SESSION_COOKIE_NAME='epic_stock_scale',STOCK_ECONOMICS_POLICY='DEMO_ORIGIN_FIFO_V1')
sys.path.insert(0,str(repo/'v2'))
from app.foundation.database import engine
from sqlalchemy import text
from sqlalchemy.orm import Session
with engine.connect() as db:
    assert db.execute(text('select inet_server_port()')).scalar()==5446
    assert Path(db.execute(text('show data_directory')).scalar()).resolve()==(lab/'postgres-final-unit').resolve()
if '--prepare' in sys.argv:
    from alembic.config import Config
    from alembic import command
    os.chdir(repo/'v2');command.upgrade(Config('alembic.ini'),'head')
    from app.identity.seed import ensure_seed
    from app.catalog import public as catalog
    from app.catalog.models import Product
    from app.inventory import public as inventory
    with Session(engine) as db:
        ensure_seed(db,email='admin@epic.com.br',password='admin123',name='Escala isolada')
        catalog.ensure_taxonomy(db);cats,types=catalog.taxonomy_catalog(db);kind=next(t for t in types if t.slug=='consumivel')
        for i in range(507):
            sku=f'SCALE-HEROES-{i:04}'
            if db.query(Product).filter_by(sku=sku).first():continue
            p=catalog.create_product(db,sku=sku,description=f'Bolas Heroes teste de escala {i:04}')
            catalog.update_product(db,p.id,unit='PCT',unit_set=True,product_type_id=kind.id,attributes={'sport':'Beach Tennis / Padel','model':'Escala','consumable_kind':'BALL','pack_qty':'3'})
            inventory.record_adjustment(db,location_code='DOMESTIC-MAIN',product_id=p.id,quantity_delta='1',reason='SCALE-only fixture')
        db.commit()
    print('507 products; separate scale cluster 5446; no main-demo writes.');raise SystemExit(0)
from app.treasury.fx_provider import set_quote_provider,FxQuoteUnavailable
class Offline:
    def get_latest_quote(self,*args,**kwargs):raise FxQuoteUnavailable('Escala isolada, sem integração externa.')
set_quote_provider(Offline())
from app.main import app
if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8089)
