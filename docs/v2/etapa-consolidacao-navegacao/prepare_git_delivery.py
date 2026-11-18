"""Separate this delivery from the already dirty working tree; leave files intact."""
from pathlib import Path
import difflib,json,os,re,subprocess
repo=Path(__file__).resolve().parents[3]
backup=repo.parent/'backups/navigation-before-20261118'
review=backup/'git-review';review.mkdir(exist_ok=True)
out=Path(__file__).parent
def git(*args,**kw):return subprocess.run(['git',*args],cwd=kw.pop('cwd',repo),capture_output=True,**kw)
def head(rel):
 r=git('show','HEAD:'+rel)
 return r.stdout.decode('utf8').replace('\r\n','\n') if r.returncode==0 else None
def read(p):return p.read_text(encoding='utf8') if p.exists() else None
changes=json.loads((out/'source-changes.json').read_text(encoding='utf8'))
paths=[row.get('file',row.get('deleted')) for row in changes]
paths+=['ROADMAP_V2_EPIC.md','docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md','v2/frontend/e2e/rbac-roles.spec.ts','v2/frontend/e2e/i9-0-shell.spec.ts','v2/frontend/e2e/helpers/orderCreate.ts']
old_patch=(backup/'working-before.patch').read_bytes()
parts=re.split(rb'(?=^diff --git )',old_patch,flags=re.M)
conflicts=[];records=[];patch=[]
for rel in paths:
 before=read(backup/rel);current=read(repo/rel);committed=head(rel)
 if rel.startswith('v2/frontend/e2e/'):
  restore=review/'reconstruct';p=restore/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(committed,encoding='utf8')
  section=next((part for part in parts if part.startswith(('diff --git a/'+rel+' b/').encode())),None)
  if section:
   applied=git('apply','--whitespace=nowarn','-',cwd=restore,input=section)
   assert applied.returncode==0,applied.stderr.decode(errors='replace')
  before=read(p)
 patch.extend(difflib.unified_diff((before or '').splitlines(True),(current or '').splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
 target=review/'staged'/rel;target.parent.mkdir(parents=True,exist_ok=True)
 if current is None:
  records.append({'path':rel,'action':'delete'});continue
 if committed is None or before==committed:
  merged=current;method='delivery-only/new'
 elif rel=='v2/frontend/src/app-shell/AppShell.tsx':
  # All pre-existing changes were the navigation being replaced in this task.
  merged=current;method='navigation fully replaced'
 else:
  files=[]
  for suffix,content in [('head',committed),('before',before),('final',current)]:
   p=review/(rel.replace('/','__')+'.'+suffix);p.write_text(content or '',encoding='utf8');files.append(p)
  result=git('merge-file','-p',str(files[0]),str(files[1]),str(files[2]))
  merged=result.stdout.decode('utf8').replace('\r\n','\n');method='three-way delta only'
  if result.returncode:
   conflicts.append(rel);method='manual review required'
 if rel.endswith('ProductAreaNav.tsx'):
  # Its old CSS was untracked before this task and remains unstaged/local.
  merged=merged.replace('import "./productArea.css";\n','');method='new compatibility stub; pre-existing CSS import left unstaged'
 target.write_text(merged,encoding='utf8')
 records.append({'path':rel,'action':'update','method':method,'conflict':rel in conflicts})
# Master existed as untracked WIP: include only this task's delta as evidence.
rel='docs/v2/etapa-pre-demo-ceo/ui-refinement/UI_EXECUTIVA_REFINEMENT_PLAN.md'
patch.extend(difflib.unified_diff(read(backup/rel).splitlines(True),read(repo/rel).splitlines(True),fromfile='a/'+rel,tofile='b/'+rel))
(out/'delivery-working-tree.patch').write_text(''.join(patch),encoding='utf8')
(review/'records.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print(json.dumps({'review':str(review),'conflicts':conflicts,'paths':len(paths)},indent=2))
