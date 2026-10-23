"""Serve an immutable local release; does not seed, migrate, restore or reset."""
import os,sys
from pathlib import Path
root=Path(sys.argv[1]).resolve();port=int(sys.argv[2]) if len(sys.argv)>2 else 8082
assert root.name=='laptop-prices-20261023' and port in (8082,8091)
os.environ.update(APP_ENV='test',DATABASE_URL='postgresql://postgres@127.0.0.1:5449/epic_v2_test',
 ATTACHMENTS_PATH=str(root/'storage/attachments'),QUARANTINE_PATH=str(root/'storage/quarantine'),
 LOGS_PATH=str(root/'logs'),FRONTEND_DIST_PATH=str(root/'v2/frontend/dist'),
 SESSION_COOKIE_NAME='epic_laptop_release',STOCK_ECONOMICS_POLICY='DEMO_ORIGIN_FIFO_V1',PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0,str(root/'v2'))
from app.foundation.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    name,dbport,folder=conn.execute(text("select current_database(),inet_server_port(),current_setting('data_directory')")).one()
    assert name=='epic_v2_test' and dbport==5449 and Path(folder).resolve()==(root/'postgres').resolve()
from app.treasury.fx_provider import set_quote_provider,FxQuoteUnavailable
class Offline:
    def get_latest_quote(self,foreign,base='BRL'):
        raise FxQuoteUnavailable('Atualização externa desativada na demonstração.')
set_quote_provider(Offline())
from app.main import app
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=port)
