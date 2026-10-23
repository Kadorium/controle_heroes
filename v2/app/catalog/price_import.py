"""Pure CSV preview, optimistic snapshot validation and one atomic confirmation."""
import csv,io,json
from datetime import date
from app.catalog.models import Product,SalesPriceList
from app.catalog.errors import CatalogValidationError
from app.catalog.price_changes import active_rows,prepare_price,apply_price,digest,replay,remember
from app.catalog.pricing import price_dict
from app.audit import public as audit

def parse_csv(content):
    if len(content.encode('utf8'))>1_000_000:raise CatalogValidationError('Arquivo excede 1 MB.')
    content=content.lstrip('\ufeff')
    delimiter=';' if ';' in content.split('\n',1)[0] else ','
    reader=csv.DictReader(io.StringIO(content),delimiter=delimiter,strict=True)
    required={'sku','preco','unidade','inicio','fim','acao'}
    if not reader.fieldnames or len(reader.fieldnames)!=6 or set(reader.fieldnames)!=required:raise CatalogValidationError('Cabeçalho: sku;preco;unidade;inicio;fim;acao. Use UTF-8.')
    try:rows=list(reader)
    except csv.Error:raise CatalogValidationError('CSV inválido. Confira as aspas e os separadores de cada linha.')
    if not rows or len(rows)>500:raise CatalogValidationError('Envie de 1 a 500 linhas.')
    return rows

def preview_prices(db,*,list_id,csv_text):
    table=db.get(SalesPriceList,list_id)
    if not table:raise CatalogValidationError('Selecione uma tabela existente.')
    result=[];seen=set();states=[]
    for line,row in enumerate(parse_csv(csv_text),2):
        item={'line':line,'sku':(row.get('sku') or '').strip(),'action':'rejected','error':None}
        try:
            if None in row or any(v is None for v in row.values()):raise CatalogValidationError('Quantidade de colunas diferente do cabeçalho.')
            product=db.query(Product).filter_by(sku=item['sku']).first()
            if not product:raise CatalogValidationError('SKU não encontrado. Cadastre o produto antes de importar.')
            if product.id in seen:raise CatalogValidationError('SKU repetido no arquivo. Use uma linha por produto.')
            seen.add(product.id)
            try:start=date.fromisoformat(row['inicio'].strip());end=date.fromisoformat(row['fim'].strip()) if row['fim'].strip() else None
            except ValueError:raise CatalogValidationError('Data inválida. Use AAAA-MM-DD.')
            action={'criar':'create','substituir':'replace'}.get(row['acao'].strip().lower())
            if not action:raise CatalogValidationError('Ação inválida: criar ou substituir.')
            item.update(prepare_price(db,product=product,list_id=list_id,amount=row['preco'].strip().replace(',','.'),unit=row['unidade'].strip(),start=start,end=end,action=action))
            states.extend(price_dict(p) for p in active_rows(db,product.id,list_id))
        except CatalogValidationError as e:item['error']=e.message;item['action']='rejected'
        result.append(item)
    table_state={'id':table.id,'name':table.name,'channel':table.channel,'currency':table.currency,'nature':table.nature}
    return {'rows':result,'valid':all(x['action']!='rejected' for x in result),'table':table_state,
        'token':digest({'rows':result,'state':states,'table':table_state})}

def confirm_prices(db,*,actor_id,list_id,csv_text,preview_token,request_key,reason):
    payload={'list_id':list_id,'csv_hash':digest(csv_text),'preview_token':preview_token,'reason':reason}
    old=replay(db,request_key,actor_id,payload)
    if old is not None:return old
    if not reason.strip():raise CatalogValidationError('Informe o motivo da importação.')
    skus=[r.get('sku','').strip() for r in parse_csv(csv_text)]
    db.query(Product).filter(Product.sku.in_(skus)).order_by(Product.id).with_for_update().all()
    preview=preview_prices(db,list_id=list_id,csv_text=csv_text)
    if not preview['valid']:raise CatalogValidationError('Corrija as linhas rejeitadas antes de confirmar. Nada foi importado.')
    if preview['token']!=preview_token:raise CatalogValidationError('Os preços mudaram desde a prévia. Confira uma nova prévia antes de confirmar.')
    changes=[]
    for p in preview['rows']:
        changes.append(apply_price(db,p,actor=actor_id,key=digest([request_key,p['line']]),reason=reason))
    result={'confirmed':len(changes),'changes':changes,'preview_token':preview_token}
    audit.record_event(db,actor_id=str(actor_id),entity_type='sales_price_import',entity_id=request_key,action='confirm',reason_code='SALES_PRICE_IMPORT',details=json.dumps({'reason':reason,'changes':changes},ensure_ascii=False))
    return remember(db,request_key,actor_id,payload,result)
