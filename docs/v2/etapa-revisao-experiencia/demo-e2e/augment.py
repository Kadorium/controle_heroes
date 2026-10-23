"""Journaled preparation of roles, BRL obligations and physical alternate states."""
import seed as s
from sqlalchemy.orm import Session
from app.identity.seed import ensure_e2e_operator_users
with Session(s.runtime.engine) as db:
    ensure_e2e_operator_users(db);db.commit()
for story in s.stories:
    if not story.get('funding'):continue
    f=story['funding'];proc=story['process']
    current=s.api('GET',f"/import-processes/{proc['id']}/funding-requests/{f['id']}")
    if current['status']=='DRAFT':
        s.step(story['key']+'-funding-confirm','POST',f"/import-processes/{proc['id']}/funding-requests/{f['id']}/confirm",{'expected_version':current['version']})
print('Operator roles and BRL obligations prepared; no duplicate business records.')
