"""One explicitly fictional transport document, seeded only in the verified lab."""
from pathlib import Path
import json, importlib.util, httpx
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine,text
out=Path(__file__).resolve().parent
repo=out.parents[2];lab=repo.parent/'audit-lab/navigation-20261118'
with create_engine('postgresql://postgres@127.0.0.1:5460/epic_v2_test').connect() as db:
 name,port,folder=db.execute(text("select current_database(),inet_server_port(),current_setting('data_directory')")).one()
 assert name=='epic_v2_test' and port==5460 and Path(folder).resolve()==(lab/'postgres').resolve()
p=lab/'NAV18-packing-ficticio.pdf'
c=canvas.Canvas(str(p),pagesize=(595,842));c.setTitle('NAV18 - documento ficticio de teste')
c.setFont('Helvetica-Bold',20);c.drawString(48,780,'NAV18 - PACKING LIST')
c.setFont('Helvetica',12)
for y,t in [(744,'DOCUMENTO FICTICIO - ENSAIO ISOLADO'),(710,'Origem: Fornecedor NAV18'),(686,'Destino: Armazem de teste NAV18'),(640,'Produto: NAV18-RECEBIMENTO'),(616,'Quantidade: 10 UN'),(592,'Volumes: 1 caixa'),(520,'Usado apenas para validar a navegacao e a conferencia.')]:c.drawString(48,y,t)
c.showPage();c.save()
# The application's PDF viewer renders this fixture during the UI verification.
client=httpx.Client(base_url='http://127.0.0.1:8102',timeout=60)
def api(method,path,**kw):
 r=client.request(method,'/api'+path,**kw);r.raise_for_status();return r.json()
api('POST','/auth/dev-login')
batch=api('POST','/ingestion/batches',json={'notes':'NAV18 documento fictício de transporte'})
upload=api('POST',f"/ingestion/batches/{batch['id']}/files",files=[('files',(p.name,p.read_bytes(),'application/pdf'))])
occ=upload['results'][0];assert occ['status']=='STORED'
doc=api('POST','/ingestion/documents',json={'occurrence_id':occ['id'],'doc_type':'PACKING_LIST_DETAIL','adapter_id':'nav18_synthetic_fixture','sections':[{'section_key':'header','title':'Documento fictício NAV18'}],'fields':[{'section_key':'header','field_key':'document_number','raw_value':'NAV18-PACKING-FICTICIO'}]})
(out/'document-fixture.json').write_text(json.dumps({'document_id':doc['id'],'occurrence_id':occ['id'],'batch_id':batch['id'],'pdf':str(p),'preparation':'API; fictional values; no commit to shipment'},indent=2),encoding='utf8')
print(json.dumps({'document_id':doc['id'],'pdf':str(p)}))
