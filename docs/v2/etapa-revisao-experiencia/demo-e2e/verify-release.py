"""Read-only release proof: HTTP bytes, manifest, source/storage hashes and database identity."""
import json,hashlib
from pathlib import Path
import httpx
from sqlalchemy import create_engine,text
repo=Path(__file__).resolve().parents[4];lab=repo.parent/'audit-lab/stock-executive-20261023';release=repo.parent/'audit-runtime/stock-executive-20261023'
client=httpx.Client(base_url='http://127.0.0.1:8082',timeout=60);client.post('/api/auth/dev-login').raise_for_status()
health=client.get('/api/health').raise_for_status().json();assert health['app_env']=='test' and health['alembic_head']=='032' and health['logical_database']=='epic_v2_test'
build=client.get('/assets/build-info.json').raise_for_status().json();assert build['build_id']=='stock-executive-20261023.1' and not build['uncommitted_candidate']
for name,expected in build['assets'].items():assert hashlib.sha256(client.get('/assets/'+name).raise_for_status().content).hexdigest()==expected
raw=client.get('/assets/demo-manifest.json').raise_for_status().content;assert hashlib.sha256(raw).hexdigest()==build['manifest_sha256'];manifest=json.loads(raw)
for check in manifest['checks']:
    actual=client.get(check['path']).raise_for_status().json()
    for path,value in check['fields'].items():
        found=actual
        for k in path.split('.'):found=found[int(k)] if isinstance(found,list) else found[k]
        assert found==value,(path,found,value)
for doc in manifest['documents']:assert hashlib.sha256(client.get(doc['url']).raise_for_status().content).hexdigest()==doc['sha256']
proof=json.loads((release/'release.json').read_text(encoding='utf-8-sig'))
for f in proof['files']:assert hashlib.sha256((release/f['path']).read_bytes()).hexdigest().upper()==f['sha256']
baseline=json.loads((lab/'after-seed-final.json').read_text(encoding='utf8'))
with create_engine('postgresql://postgres@127.0.0.1:5447/epic_v2_test').connect() as c:
    c.execute(text('SET TRANSACTION READ ONLY'))
    identity=c.execute(text("select current_database(),inet_server_port(),current_setting('data_directory'),system_identifier from pg_control_system()")).one()
    assert identity[0]=='epic_v2_test' and identity[1]==5447 and Path(identity[2]).resolve()==(release/'postgres').resolve()
    for t,expected in baseline['tables'].items():
        rows=sorted(c.execute(text(f'select row_to_json(t)::text from "{t}" t')).scalars())
        assert len(rows)==expected['count'] and hashlib.sha256('\n'.join(rows).encode()).hexdigest()==expected['sha256'],t
result={'url':str(client.base_url),'health':health,'build':build,'database':[str(v) for v in identity], 'business_sha256':baseline['sha256'],'files_checked':len(proof['files']),'manifest_checks':len(manifest['checks']),'documents_checked':len(manifest['documents']),'backup':proof['backup'],'dump_sha256':proof['dump_sha256']}
(lab/'release-proof.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result))
