"""Journaled preparation of roles, BRL obligations and physical alternate states."""
import seed as s
import json
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
for key,product,location,quantity in [('bonded',s.products[6],'BONDED-MAIN','5'),('quarantine',s.products[24],'QUARANTINE-MAIN','2')]:
    s.step('alternate-'+key,'POST','/inventory/adjustments',{'product_id':product['id'],'location_code':location,'quantity_delta':quantity,'reason':s.CODE+' saldo sintético de '+key+' sem origem de custo; não disponível para venda'})
ongoing=s.purchase('F1',[(s.products[2],11,160)],25,installments=3,receive=[],stages=2)
(s.OUT/'supplemental.json').write_text(json.dumps({'in_transit':ongoing},ensure_ascii=False,indent=2),encoding='utf8')
print('Roles, BRL obligations and isolated physical states prepared; journal prevents duplication.')
