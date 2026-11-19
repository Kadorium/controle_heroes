from pathlib import Path
import hashlib,json,shutil,socket
from datetime import datetime,timezone
repo=Path(__file__).resolve().parents[3];root=repo.parent;out=Path(__file__).parent;runtime=root/'audit-runtime/executive-20261117';backup=root/'backups/finish-before-20261119';dist=repo/'v2/frontend/dist-finish'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for file in ['unit-tests.json','isolated-unit.json']:
 tests=json.loads((out/file).read_text(encoding='utf8'));assert tests['success'] and tests['numFailedTests']==0 and tests['numPassedTests']>=30
for file in ['ui-measurements.json','interaction-results.json','financial-detail.json']:
 proof=json.loads((out/file).read_text(encoding='utf8'));assert not proof.get('failure') and not proof['errors'] and not proof['writes']
proof=json.loads((out/'ui-measurements.json').read_text(encoding='utf8'));assert proof['indexSha256']==sha(dist/'index.html') and len(proof['ap'])==4 and len(proof['headers'])==24
with socket.socket() as probe:assert probe.connect_ex(('127.0.0.1',8082))!=0,'Stop only the verified HTTP server first'
manifest=json.loads((runtime/'release.json').read_text(encoding='utf8'));assert manifest['build_id']=='executive-20261118.2';assert sha(runtime/'release.json')==sha(backup/'release.json')
for row in manifest['files']:assert sha(runtime/row['path'])==row['sha256'],row['path']
tested={'build':'executive-20261119.1','files':{p.relative_to(dist).as_posix():sha(p) for p in sorted(dist.rglob('*')) if p.is_file()}};(out/'candidate-assets.json').write_text(json.dumps(tested,indent=2),encoding='utf8')
shutil.copytree(dist,runtime/'v2/frontend/dist',dirs_exist_ok=True)
info={k:manifest[k] for k in ('source_commit','manifest_sha256')}
info.update(build_id=tested['build'],uncommitted_candidate=True,contains_preserved_wip=True,delivery_baseline_commit='a1b1719ec4a2b925d44e12455c6432e896e40364',delivery_commit=None,delivery='financial-finishing-20261119',tested_index_sha256=proof['indexSha256'])
(runtime/'v2/frontend/dist/assets/build-info.json').write_text(json.dumps(info,indent=2),encoding='utf8')
files=[{'path':p.relative_to(runtime).as_posix(),'sha256':sha(p)} for folder in ('v2/app','v2/alembic','v2/frontend/dist') for p in sorted((runtime/folder).rglob('*')) if p.is_file() and '__pycache__' not in p.parts]
manifest.update(info,files=files,created_at=datetime.now(timezone.utc).isoformat(),previous_frontend=str(backup/'release-frontend'),changes='Financial queue presentation and work-header actions distributed by measured available width')
(runtime/'release.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
(out/'promotion.json').write_text(json.dumps({'build':info['build_id'],'verified_files':len(files),'index_sha256':sha(dist/'index.html'),'backend_changed':False,'database_changed':False,'previous_frontend':str(backup/'release-frontend')},indent=2),encoding='utf8')
print(json.dumps({'build':info['build_id'],'verified_files':len(files),'index_sha256':sha(dist/'index.html')}))
