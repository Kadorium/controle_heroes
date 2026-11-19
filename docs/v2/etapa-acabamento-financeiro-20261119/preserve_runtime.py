"""Read-only evidence for the exact demonstration database and runtime."""
from pathlib import Path
import json,hashlib,sys
from sqlalchemy import create_engine,text
out=Path(__file__).parent;repo=out.parents[2];runtime=repo.parent/'audit-runtime/executive-20261117'
engine=create_engine('postgresql://postgres@127.0.0.1:5458/epic_v2_test')
with engine.connect() as db:
 db.execute(text('SET TRANSACTION READ ONLY'))
 name,port,folder=db.execute(text("select current_database(),inet_server_port(),current_setting('data_directory')")).one()
 assert name=='epic_v2_test' and port==5458 and Path(folder).resolve()==(runtime/'postgres').resolve()
 tables=[r[0] for r in db.execute(text("select tablename from pg_tables where schemaname='public' and tablename not in ('audit_log','user_sessions') order by tablename"))]
 hashes={table:db.execute(text('SELECT md5(COALESCE(string_agg(row_to_json(t)::text, chr(10) ORDER BY row_to_json(t)::text),\'\')) FROM public."'+table+'" t')).scalar() for table in tables}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
backend={p.relative_to(runtime).as_posix():sha(p) for path in ['v2/app','v2/alembic'] for p in sorted((runtime/path).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
d={'database':name,'port':port,'data_directory':folder,'tables':hashes,'backend':backend,'launcher_config_sha256':sha(repo/'scripts/launcher/launcher.json'),'launcher_cache_helper_sha256':sha(repo/'scripts/launcher/release_url.py'),'launcher_source_sha256':sha(repo/'scripts/launcher/start_epic.py')}
if sys.argv[1]=='before':(out/'runtime-before.json').write_text(json.dumps(d,indent=2),encoding='utf8')
else:
 before=json.loads((out/'runtime-before.json').read_text(encoding='utf8'));(out/'runtime-after.json').write_text(json.dumps(d,indent=2),encoding='utf8')
 changed=[key for key,value in hashes.items() if before['tables'][key]!=value]
 assert set(changed)<= {'users'},changed
 for key in d:
  if key!='tables':assert before[key]==d[key],key
 (out/'runtime-preserved.json').write_text(json.dumps({'database':name,'port':port,'domain_tables_unchanged':len(hashes)-1,'backend_files_unchanged':len(backend),'launcher_config_and_cache_unchanged':True,'no_test_data_promoted':True,'authentication_table_changed':changed,'authentication_note':'users hash changes with login; actual backend identity/public.py:142 updates last_login. Original before/after hashes retained; users, sessions and audit excluded from business immutability claim.'},indent=2),encoding='utf8')
print(json.dumps({'phase':sys.argv[1],'domain_tables':len(hashes),'backend_files':len(backend)}))
