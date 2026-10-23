"""Read-only HTTP + file + database proof. Session creation is not a business mutation."""
import json,hashlib,sys
from pathlib import Path
import httpx
from sqlalchemy import create_engine,text
repo=Path(__file__).resolve().parents[4];release=repo.parent/'audit-runtime/laptop-prices-20261023';lab=repo.parent/'audit-lab/stock-executive-20261023'
port=int(sys.argv[1]) if len(sys.argv)>1 else 8082
client=httpx.Client(base_url=f'http://127.0.0.1:{port}',timeout=60);client.post('/api/auth/dev-login').raise_for_status()
health=client.get('/api/health').raise_for_status().json();assert health['app_env']=='test' and health['alembic_head']=='033' and health['schema_ok'] and health['logical_database']=='epic_v2_test'
build=client.get('/assets/build-info.json').raise_for_status().json();assert build['build_id']=='laptop-prices-20261023.1' and not build['uncommitted_candidate']
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
with create_engine('postgresql://postgres@127.0.0.1:5449/epic_v2_test').connect() as c:
    c.execute(text('SET TRANSACTION READ ONLY'))
    identity=c.execute(text("select current_database(),inet_server_port(),current_setting('data_directory'),system_identifier from pg_control_system()")).one()
    assert identity[0]=='epic_v2_test' and identity[1]==5449 and Path(identity[2]).resolve()==(release/'postgres').resolve()
result={'url':str(client.base_url),'health':health,'build':build,'database':[str(v) for v in identity],'files_checked':len(proof['files']),'manifest_checks':len(manifest['checks']),'documents_checked':len(manifest['documents']),'backup':proof['backup'],'dump_sha256':proof['dump_sha256']}
tables=['products','orders','invoices','payables','payments','payment_allocations','shipments','import_processes','inventory_movements','costing_cases','costing_versions','documents','sales_price_entries','sales_price_operations']
fingerprints={}
for dbport in (5445,5449):
    with create_engine(f'postgresql://postgres@127.0.0.1:{dbport}/epic_v2_test').connect() as c:
        c.execute(text('SET TRANSACTION READ ONLY'))
        expected=lab/'postgres' if dbport==5445 else release/'postgres'
        assert Path(c.execute(text('show data_directory')).scalar()).resolve()==expected.resolve()
        fingerprints[dbport]={}
        for table in tables:
            rows=sorted(c.execute(text(f'select row_to_json(t)::text from {table} t')).scalars())
            fingerprints[dbport][table]={'count':len(rows),'sha256':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
assert fingerprints[5445]==fingerprints[5449], 'Business state differs from frozen candidate'
result['business_tables_equal']=fingerprints[5449]
(lab/f'laptop/release-proof-{port}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result))
