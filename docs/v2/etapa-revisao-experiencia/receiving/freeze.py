"""Validate the preserved Heroes manifest, then identify only the compiled bundle."""
import json,hashlib,subprocess,shutil
from pathlib import Path
import httpx
repo=Path(__file__).resolve().parents[4];lab=repo.parent/'audit-lab/receiving-20261023'
assets=repo/'v2/frontend/dist/assets'
client=httpx.Client(base_url='http://127.0.0.1:8092',timeout=60)
client.post('/api/auth/dev-login').raise_for_status()
manifest=json.loads((lab/'demo-manifest.json').read_text(encoding='utf8'))
for check in manifest['checks']:
    data=client.get(check['path']).raise_for_status().json()
    for path,value in check['fields'].items():
        found=data
        for part in path.split('.'):found=found[int(part)] if isinstance(found,list) else found[part]
        assert found==value,(path,found,value)
for doc in manifest['documents']:
    assert hashlib.sha256(client.get(doc['url']).raise_for_status().content).hexdigest()==doc['sha256']
shutil.copy2(lab/'demo-manifest.json',assets/'demo-manifest.json')
revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
dirty=bool(subprocess.check_output(['git','status','--porcelain','--','v2/app','v2/frontend/src','v2/alembic'],cwd=repo,text=True).strip())
build={'build_id':'receiving-stock-20261023.1','source_commit':revision,'uncommitted_candidate':dirty,
 'manifest_sha256':hashlib.sha256((assets/'demo-manifest.json').read_bytes()).hexdigest(),
 'assets':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in assets.iterdir() if p.suffix in ('.js','.css','.mjs')}}
(assets/'build-info.json').write_text(json.dumps(build,indent=2),encoding='utf8')
print(json.dumps({'checks':len(manifest['checks']),'documents':len(manifest['documents']),'build':build}))
