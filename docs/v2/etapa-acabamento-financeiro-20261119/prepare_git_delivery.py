"""Prepare a reviewable tree; never replace or stage the working tree."""
from pathlib import Path
import json,difflib,subprocess
repo=Path.cwd();backup=repo.parent/'backups/finish-before-20261119';out=Path(__file__).parent;review=backup/'git-review';review.mkdir(exist_ok=True)
BASE='a1b1719ec4a2b925d44e12455c6432e896e40364'
def git(*a):return subprocess.run(['git',*a],cwd=repo,capture_output=True)
assert git('rev-parse','HEAD').stdout.decode().strip()==BASE
paths=[]
for p in (repo/'v2/frontend/src').rglob('*'):
 if p.is_file():
  rel=p.relative_to(repo).as_posix();before=backup/rel
  if not before.exists() or p.read_text(encoding='utf-8-sig')!=before.read_text(encoding='utf-8-sig'):paths.append(rel)
for rel in ['ROADMAP_V2_EPIC.md','docs/v2/blueprint UIUX/BLUEPRINT_UI_UX_EPIC_v3.md']:
 if (repo/rel).read_text(encoding='utf-8-sig')!=(backup/rel).read_text(encoding='utf-8-sig'):paths.append(rel)
records=[];delta=[];conflicts=[]
for rel in paths:
 before=(backup/rel).read_text(encoding='utf-8-sig') if (backup/rel).exists() else '';current=(repo/rel).read_text(encoding='utf-8-sig');r=git('show',BASE+':'+rel);head=r.stdout.decode('utf8').replace('\r\n','\n') if r.returncode==0 else None
 delta+=list(difflib.unified_diff(before.splitlines(True),current.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel,n=0));merged=current;method='delivery only'
 if head is not None and head!=before:
  files=[]
  for tag,content in [('head',head),('before',before),('after',current)]:
   p=review/(rel.replace('/','__')+'.'+tag);p.write_text(content,encoding='utf8');files.append(p)
  r=git('merge-file','-p',*[str(p) for p in files]);merged=r.stdout.decode('utf8').replace('\r\n','\n');method='three-way delta, prior WIP excluded'
  if r.returncode:
   if rel.endswith('/apQueue.css') or rel.endswith('/apQueueColumns.tsx'):
    merged=current;method='presentation replaced in this scope; previous widths superseded'
   elif rel.endswith('/ApQueuePage.tsx'):
    import re
    merged=re.sub(r'<<<<<<<[^\n]*\n.*?=======\n.*?>>>>>>>[^\n]*\n','        </div>\n',merged,flags=re.S);method='delivery delta; existing pagination WIP excluded'
   elif rel.endswith('/OperationalTable.tsx'):
    import re
    merged=re.sub(r'<<<<<<<[^\n]*\n.*?=======\n.*?>>>>>>>[^\n]*\n','      <div className={wrapClass} role={scrollLabel ? "region" : undefined} aria-label={scrollLabel} tabIndex={scrollLabel ? 0 : undefined}>\n        <table className={tableClass} {...rest}>\n',merged,flags=re.S);method='only opt-in scroll accessibility; prior global minWidth/data attributes excluded'
   else:conflicts.append(rel)
 target=review/'staged'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged,encoding='utf8')
 records.append({'path':rel,'method':method,'priorWIP':head is not None and head!=before})
rel='docs/v2/etapa-pre-demo-ceo/ui-refinement/UI_EXECUTIVA_REFINEMENT_PLAN.md';before=(backup/rel).read_text(encoding='utf8');current=(repo/rel).read_text(encoding='utf8');delta+=list(difflib.unified_diff(before.splitlines(True),current.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel,n=0))
(out/'source-changes.json').write_text(json.dumps(records,indent=2),encoding='utf8');(out/'delivery-working-tree.patch').write_text(''.join(delta),encoding='utf8');(review/'records.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print(json.dumps({'prepared':len(records),'conflicts':conflicts,'review':str(review)}))
