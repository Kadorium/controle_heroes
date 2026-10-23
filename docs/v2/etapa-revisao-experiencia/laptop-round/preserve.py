"""Snapshot current demonstration and WIP before laptop/price work; never restores."""
import hashlib,json,shutil,subprocess
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine,text
import httpx
repo=Path(__file__).resolve().parents[4];epic=repo.parent
release=epic/'audit-runtime/stock-executive-20261023'
lab=epic/'audit-lab/stock-executive-20261023'
out=epic/'backups'/('laptop-prices-before-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True,exist_ok=False)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
git=lambda *a:subprocess.check_output(['git',*a],cwd=repo).decode('utf8').strip()
health=httpx.get('http://127.0.0.1:8082/api/health').raise_for_status().json()
build=httpx.get('http://127.0.0.1:8082/assets/build-info.json').raise_for_status().json()
assert build['source_commit']=='88718645c830b16ee4e7860eb17cc3ffbf9d58fa' and health['alembic_head']=='032'
pg=Path('C:/Program Files/PostgreSQL/18/bin');identities={}
for port,folder,name in [(5447,release/'postgres','presentation'),(5445,lab/'postgres','candidate')]:
    with create_engine(f'postgresql://postgres@127.0.0.1:{port}/epic_v2_test').connect() as c:
        c.execute(text('SET TRANSACTION READ ONLY'))
        row=c.execute(text('select current_database(),inet_server_port(),current_setting(\'data_directory\'),system_identifier from pg_control_system()')).one()
        assert row[0]=='epic_v2_test' and row[1]==port and Path(row[2]).resolve()==folder.resolve()
        identities[name]=[str(x) for x in row]
    dump=out/(name+'.dump')
    subprocess.run([str(pg/'pg_dump.exe'),'-h','127.0.0.1','-p',str(port),'-U','postgres','-d','epic_v2_test','-Fc','-f',str(dump)],check=True)
    subprocess.run([str(pg/'pg_restore.exe'),'-f','NUL',str(dump)],check=True)
files=[]
def save(p,relative):
    dest=out/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
    digest=sha(p);assert sha(dest)==digest;files.append({'path':str(relative),'sha256':digest})
for root,parts,label in [(release,['v2/app','v2/alembic','v2/frontend/dist','storage','release-runtime.py','release.json','demo-manifest.json'],'release'),(lab,['storage','scenario'],'candidate')]:
    for part in parts:
        p=root/part
        for f in p.rglob('*') if p.is_dir() else [p]:
            if f.is_file() and f.suffix!='.pyc':save(f,Path(label)/f.relative_to(root))
# Every current changed/untracked file; ignored credentials only in explicit runtime backup above.
paths=set(subprocess.check_output(['git','ls-files','-m','-o','--exclude-standard','-z'],cwd=repo).decode('utf8').split('\0'))-{''}
for relative in sorted(paths):
    f=repo/relative
    if f.is_file():save(f,Path('wip')/relative)
for f in [repo/'docs/v2/etapa-pre-demo-ceo/scripts/open-demo-presenter.ps1',repo/'docs/v2/etapa-revisao-experiencia/demo-e2e/start-release.ps1']:
    save(f,Path('launchers')/f.name)
record={'at':datetime.now().astimezone().isoformat(),'destination':str(out),'branch':git('branch','--show-current'),'head':git('rev-parse','HEAD'),'remote':git('ls-remote','origin','refs/heads/feat/stock-executive-20261023'),'health':health,'build':build,'identities':identities,'files':files,'dumps':{f.name:sha(f) for f in out.glob('*.dump')}}
(out/'preservation.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'destination':str(out),'files':len(files),'identities':identities,'dumps':record['dumps']}))
