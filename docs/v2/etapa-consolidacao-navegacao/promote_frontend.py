"""Promote exactly the UI-tested assets; no backend, migration, or database writes."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,shutil,socket
repo=Path(__file__).resolve().parents[3];root=repo.parent
runtime=root/'audit-runtime/executive-20261117';backup=root/'backups/navigation-before-20261118'
dist=repo/'v2/frontend/dist-navigation';out=Path(__file__).parent
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
with socket.socket() as probe:
 assert probe.connect_ex(('127.0.0.1',8082))!=0,'Stop only the verified release server first'
manifest=json.loads((runtime/'release.json').read_text(encoding='utf8'))
assert manifest['build_id']=='executive-20261117.4'
assert sha(backup/'release.json')==sha(runtime/'release.json')
for f in manifest['files']:assert sha(runtime/f['path'])==f['sha256'],f['path']
tested=json.loads((out/'candidate-assets.json').read_text(encoding='utf8'))
for name,digest in tested['files'].items():assert sha(dist/name)==digest,name
assert json.loads((out/'ui/smoke.json').read_text(encoding='utf8'))['errors']==[]
assert all(row['result']=='PASS' for row in json.loads((out/'ui/journeys.json').read_text(encoding='utf8'))['results'])
shutil.copytree(dist,runtime/'v2/frontend/dist',dirs_exist_ok=True)
info={k:manifest[k] for k in ('source_commit','uncommitted_candidate','manifest_sha256')}
info.update(build_id=tested['build'],assets={p.name:sha(p) for p in (runtime/'v2/frontend/dist/assets').iterdir() if p.is_file() and p.suffix in ('.js','.css','.mjs')},navigation_delivery='docs/v2/etapa-consolidacao-navegacao')
(runtime/'v2/frontend/dist/assets/build-info.json').write_text(json.dumps(info,indent=2),encoding='utf8')
files=[{'path':p.relative_to(runtime).as_posix(),'sha256':sha(p)} for folder in ('v2/app','v2/alembic','v2/frontend/dist') for p in sorted((runtime/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
manifest.update(info,files=files,created_at=datetime.now(timezone.utc).isoformat(),previous_frontend=str(backup/'release-frontend'),changes='Executive area navigation; authorized fallbacks; context-preserving links')
(runtime/'release.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
proof={'build':info['build_id'],'files_verified':len(files),'backend_changed':False,'database_changed':False,'candidate_index_sha256':sha(dist/'index.html'),'release_index_sha256':sha(runtime/'v2/frontend/dist/index.html'),'backup':str(backup)}
(out/'promotion.json').write_text(json.dumps(proof,indent=2),encoding='utf8');print(json.dumps(proof))
