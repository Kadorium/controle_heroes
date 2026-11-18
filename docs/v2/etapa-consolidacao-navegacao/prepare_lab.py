"""Create a dedicated test copy; never reset or mutate the source database."""
from pathlib import Path
import json, os, shutil, subprocess, sys, tempfile

repo = Path(__file__).resolve().parents[3]
epic = repo.parent
lab = epic / 'audit-lab/navigation-20261118'
release = epic / 'audit-runtime/executive-20261117'
pg = Path('C:/Program Files/PostgreSQL/18/bin')
lab.mkdir(parents=True, exist_ok=True)
def run(name, *args):
    with tempfile.TemporaryFile(mode='w+', encoding='utf8') as log:
        result = subprocess.run([str(pg/name), *map(str,args)], check=True, stdout=log, stderr=log)
        log.seek(0)
        result.stdout = log.read()
        return result
source = run('psql.exe','-h','127.0.0.1','-p','5458','-U','postgres','-d','epic_v2_test','-At','-c',"select current_database(),inet_server_port(),current_setting('data_directory')").stdout.strip()
assert source.split('|')[:2] == ['epic_v2_test','5458'] and Path(source.split('|')[2]).resolve() == (release/'postgres').resolve()
if not (lab/'postgres').exists():
    run('pg_dump.exe','-h','127.0.0.1','-p','5458','-U','postgres','-d','epic_v2_test','-Fc','-f',lab/'source.dump')
    run('initdb.exe','-D',lab/'postgres','-U','postgres','-A','trust','--encoding=UTF8','--locale=C')
    run('pg_ctl.exe','-D',lab/'postgres','-l',lab/'postgres.log','-o','-p 5460 -h 127.0.0.1','-w','start')
else:
    target=run('psql.exe','-h','127.0.0.1','-p','5460','-U','postgres','-d','postgres','-At','-c',"select current_setting('data_directory')").stdout.strip()
    assert Path(target).resolve()==(lab/'postgres').resolve()
run('createdb.exe','-h','127.0.0.1','-p','5460','-U','postgres','epic_v2_test')
run('pg_restore.exe','-h','127.0.0.1','-p','5460','-U','postgres','-d','epic_v2_test','--no-owner',lab/'source.dump')
shutil.copytree(release/'storage',lab/'storage',dirs_exist_ok=True)
(lab/'logs').mkdir(exist_ok=True)
runner = lab/'serve.py'
runner.write_text('''from pathlib import Path
import os,sys
root=Path(__file__).resolve().parent
repo=root.parents[1]/'Controle'
release=root.parents[1]/'audit-runtime/executive-20261117'
os.environ.update(APP_ENV='test',DATABASE_URL='postgresql://postgres@127.0.0.1:5460/epic_v2_test',ATTACHMENTS_PATH=str(root/'storage/attachments'),QUARANTINE_PATH=str(root/'storage/quarantine'),LOGS_PATH=str(root/'logs'),FRONTEND_DIST_PATH=str(repo/'v2/frontend/dist-navigation'),SESSION_COOKIE_NAME='epic_navigation_lab',STOCK_ECONOMICS_POLICY='DEMO_ORIGIN_FIFO_V1',PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0,str(release/'v2'))
from app.foundation.database import engine
from sqlalchemy import text
with engine.connect() as conn:
 name,port,folder=conn.execute(text("select current_database(),inet_server_port(),current_setting('data_directory')")).one()
 assert name=='epic_v2_test' and port==5460 and Path(folder).resolve()==(root/'postgres').resolve()
from app.treasury.fx_provider import set_quote_provider,FxQuoteUnavailable
class Offline:
 def get_latest_quote(self,foreign,base='BRL'): raise FxQuoteUnavailable('Atualização externa desativada no ensaio de navegação.')
set_quote_provider(Offline())
from app.main import app
import uvicorn
uvicorn.run(app,host='127.0.0.1',port=8102)
''',encoding='utf8')
proc = subprocess.Popen([str(repo/'v2/.venv/Scripts/python.exe'),'-B',str(runner)],stdout=(lab/'server.out').open('w'),stderr=(lab/'server.err').open('w'),creationflags=subprocess.CREATE_NO_WINDOW)
proof={'source_verified':source,'test_port':5460,'test_database':'epic_v2_test','test_data_directory':str(lab/'postgres'),'server_pid':proc.pid,'url':'http://127.0.0.1:8102','backend':str(release/'v2'),'frontend':str(repo/'v2/frontend/dist-navigation')}
(Path(__file__).parent/'lab.json').write_text(json.dumps(proof,indent=2),encoding='utf8')
print(json.dumps(proof))
