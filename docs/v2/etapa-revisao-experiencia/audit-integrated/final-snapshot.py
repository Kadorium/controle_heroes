"""Preserve final audit laboratory only. Never restore/reset or touch presentation."""
from pathlib import Path
from datetime import datetime
import hashlib,json,shutil,subprocess
from sqlalchemy import create_engine,text
repo=Path(__file__).resolve().parents[4];lab=repo.parent/'audit-lab/integrated-20261023'
with create_engine('postgresql://postgres@127.0.0.1:5452/epic_v2_test').connect() as db:
    identity=db.execute(text("select current_database(),inet_server_port(),current_setting('data_directory')")).one()
    assert identity[0]=='epic_v2_test' and identity[1]==5452 and Path(identity[2]).resolve()==(lab/'postgres').resolve()
out=repo.parent/'backups'/('integrated-final-'+datetime.now().strftime('%Y%m%d-%H%M%S'));out.mkdir(parents=True,exist_ok=False)
pg=Path('C:/Program Files/PostgreSQL/18/bin');dump=out/'audit.dump'
subprocess.run([str(pg/'pg_dump.exe'),'-h','127.0.0.1','-p','5452','-U','postgres','-d','epic_v2_test','-Fc','-f',str(dump)],check=True)
subprocess.run([str(pg/'pg_restore.exe'),'-f','NUL',str(dump)],check=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=[]
for part in ['storage','quarantine','attachments','chain.json','cost-control.json','runtime.json','v2/frontend/dist']:
    p=lab/part
    for f in p.rglob('*') if p.is_dir() else [p]:
        if f.is_file():
            dest=out/f.relative_to(lab);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest);assert sha(dest)==sha(f);files.append({'path':str(f.relative_to(lab)),'sha256':sha(dest)})
record={'at':datetime.now().astimezone().isoformat(),'destination':str(out),'database':identity[0],'port':identity[1],'dump_sha256':sha(dump),'files':files,'recovery':'Restore only into NEW isolated cluster/database; use initial preserved release code. Do not restore over 8082/5451.'}
(out/'snapshot.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
(lab/'final-snapshot.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'destination':str(out),'files':len(files),'dump_sha256':sha(dump)}))
