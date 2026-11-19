from pathlib import Path
import json,difflib,subprocess,os
repo=Path.cwd();backup=repo.parent/'backups/details-before-20261118';out=repo/'docs/v2/etapa-detalhes-recebimento-20261118';review=backup/'git-review';review.mkdir(exist_ok=True)
BASE='f601b02017f625f1bfdaa66d1d3ff12d3019dbe8'
def git(*a,**kw):return subprocess.run(['git',*a],cwd=repo,capture_output=True,**kw)
assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
assert not git('diff','--cached','--name-only').stdout
paths=[]
for folder in ['v2/frontend/src','v2/frontend/e2e']:
 for p in (repo/folder).rglob('*'):
  if p.is_file():
   rel=p.relative_to(repo).as_posix();before=backup/rel
   if not before.exists() or p.read_text(encoding='utf-8-sig')!=before.read_text(encoding='utf-8-sig'):paths.append(rel)
paths += ["ROADMAP_V2_EPIC.md","docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md","scripts/launcher/release_url.py","scripts/launcher/test_release_url.py"]
records=[];delta=[]
for rel in paths:
 p=repo/rel;before=(backup/rel).read_text(encoding='utf-8-sig') if (backup/rel).exists() else '';current=p.read_text(encoding='utf-8-sig');r=git('show',BASE+':'+rel);head=r.stdout.decode('utf8').replace('\r\n','\n') if r.returncode==0 else None
 delta+=list(difflib.unified_diff(before.splitlines(True),current.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
 method='delivery only';merged=current
 if head is not None and head!=before:
  if rel=='ROADMAP_V2_EPIC.md':
   import re
   merged=head
   for prefix in ['| Última entrega |','| Próxima entrega |','| Versão |','| Alembic head |','**Próxima ação:**']:
    new=next(line for line in current.splitlines() if line.startswith(prefix))
    merged,count=re.subn('^'+re.escape(prefix)+'.*$',lambda m:new,merged,flags=re.M);assert count==1
   new=next(line for line in current.splitlines() if line.startswith('Entrega vigente:'))
   merged,count=re.subn(r'^Auditoria atual:.*$',lambda m:new,merged,flags=re.M);assert count==1
   method='current delivery state rows only; prior WIP excluded'
  elif rel.endswith('/ReceivingPage.tsx'):
   merged=current.replace('import { HelpTip } from "../../ui/HelpTip";\n','')
   import re
   merged=re.sub(r'<HelpTip label="Entrada no estoque">.*?</HelpTip>','',merged)
   method='queue rewritten by this delivery; prior untracked HelpTip remains local'
  else:
   files=[]
   for tag,content in [('head',head),('before',before),('after',current)]:
    file=review/(rel.replace('/','__')+'.'+tag);file.write_text(content,encoding='utf8');files.append(file)
   result=git('merge-file','-p',*[str(f) for f in files]);merged=result.stdout.decode('utf8').replace('\r\n','\n')
   if result.returncode and rel=='ROADMAP_V2_EPIC.md':
    import re
    blocks=re.findall(r'<<<<<<<[^\n]*\n(.*?)=======\n(.*?)>>>>>>>[^\n]*\n',merged,re.S)
    assert len(blocks)==1 and blocks[0][0].startswith('Auditoria atual:') and blocks[0][1].startswith('Entrega vigente:')
    merged=re.sub(r'<<<<<<<[^\n]*\n.*?=======\n(.*?)>>>>>>>[^\n]*\n',lambda m:m.group(1),merged,flags=re.S)
   elif result.returncode:
    (review/(rel.replace('/','__')+'.conflict')).write_text(merged,encoding='utf8')
    raise RuntimeError('Merge requires review: '+rel)
   method='three-way delta, prior WIP excluded'
 target=review/'staged'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged,encoding='utf8')
 records.append({'path':rel,'method':method,'priorWIP':head is not None and head!=before})
rel='docs/v2/etapa-pre-demo-ceo/ui-refinement/UI_EXECUTIVA_REFINEMENT_PLAN.md'
before=(backup/rel).read_text(encoding='utf8');current=(repo/rel).read_text(encoding='utf8')
delta+=list(difflib.unified_diff(before.splitlines(True),current.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(out/'source-changes.json').write_text(json.dumps(records,indent=2),encoding='utf8');(out/'delivery-working-tree.patch').write_text(''.join(delta),encoding='utf8');(review/'records.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print(json.dumps({'prepared':len(records),'priorWIP':[r for r in records if r['priorWIP']],'review':str(review)}))
