"""Start an isolated read/write demonstration candidate; no seed on startup."""
import os
import sys
from pathlib import Path
repo = Path(__file__).resolve().parents[4]
lab = repo.parent / 'audit-lab/stock-executive-20261023'
os.environ.update(APP_ENV='test', DATABASE_URL='postgresql://postgres@127.0.0.1:5445/epic_v2_test',
    ATTACHMENTS_PATH=str(lab/'storage/attachments'), QUARANTINE_PATH=str(lab/'storage/quarantine'),
    LOGS_PATH=str(lab/'logs'), FRONTEND_DIST_PATH=str(repo/'v2/frontend/dist'),
    SESSION_COOKIE_NAME='epic_stock_candidate', STOCK_ECONOMICS_POLICY='DEMO_ORIGIN_FIFO_V1', PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0,str(repo/'v2'))
from app.foundation.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    name, port, folder = conn.execute(text("select current_database(),inet_server_port(),current_setting('data_directory')")).one()
    assert name == 'epic_v2_test' and port == 5445 and Path(folder).resolve() == (lab/'postgres').resolve()
from app.treasury.fx_provider import set_quote_provider, FxQuoteUnavailable
class Offline:
    def get_latest_quote(self, foreign, base='BRL'):
        raise FxQuoteUnavailable('Atualização externa desativada na demonstração.')
set_quote_provider(Offline())
from app.main import app
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8088)
