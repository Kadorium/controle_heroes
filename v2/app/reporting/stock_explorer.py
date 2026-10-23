"""Full-population read model. No row cap before filters, value, totals or grouping."""
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
import json
from zoneinfo import ZoneInfo
from app.catalog import public as catalog
from app.inventory import public as inventory
from app.costing import public as costing
from app.reporting.errors import ReportingError
from app.reporting.stock_economics import value_product, aggregate

def serialize(value):
    if isinstance(value,Decimal):return str(value)
    if isinstance(value,dict):return {k:serialize(v) for k,v in value.items()}
    if isinstance(value,list):return [serialize(v) for v in value]
    return value

def explorer(db, query, *, permissions, admin=False, economic_policy=True):
    can=lambda p:admin or p in permissions
    commercial=can('catalog:read');cost_access=economic_policy and can('costing:read') and can('inventory:valuation_read');price_access=economic_policy and can('catalog:prices_read')
    if (query.modality_ids or query.item_kind_ids or query.model_ids or query.group_by) and not commercial:
        raise ReportingError('Seu acesso não permite filtros comerciais',code='forbidden',status_code=403)
    products=catalog.commercial_population(db)
    physical,locations=inventory.remaining_sources(db)
    options={'modality_ids':catalog.MODALITIES.copy(),'item_kind_ids':{},'model_ids':{},'position_ids':{'DOMESTIC':'Disponível físico','BONDED':'Entreposto','QUARANTINE':'Quarentena'},'location_ids':{str(l['id']):l['name'] for l in locations}}
    for p in products:
        options['item_kind_ids'][p['item_kind_id']]=p['item_kind_label'];options['model_ids'][p['model_id']]=p['model_label']
    for field in options:
        invalid=[v for v in getattr(query,field) if str(v) not in options[field]]
        if invalid:raise ReportingError('Seleção não disponível. Revise os filtros.',code='invalid_stock_filter',status_code=422,details={'field':field,'ids':invalid})
    chosen=defaultdict(list)
    for p in physical:
        if query.position_ids and p['location']['regime'] not in query.position_ids:continue
        if query.location_ids and p['location']['id'] not in query.location_ids:continue
        if not p['location']['active']:continue
        chosen[p['product_id']].append(p)
    def matches(p,skip=None):
        if query.product_id and p['product_id']!=query.product_id:return False
        if query.q and query.q.casefold() not in (p['name']+' '+p['sku']).casefold():return False
        for key,row_key in [('modality_ids','modality_ids'),('item_kind_ids','item_kind_id'),('model_ids','model_id')]:
            vals=getattr(query,key)
            if key!=skip and vals and not set(vals).intersection(p[row_key] if isinstance(p[row_key],list) else [p[row_key]]):return False
        qty=sum((v['quantity'] for v in chosen[p['product_id']]),Decimal(0))
        return not (query.status=='positive' and qty<=0 or query.status=='zero' and qty!=0)
    population=[p for p in products if matches(p)]
    fac={}
    for field in ('modality_ids','item_kind_ids','model_ids'):
        counts=defaultdict(int)
        row_key={'modality_ids':'modality_ids','item_kind_ids':'item_kind_id','model_ids':'model_id'}[field]
        for p in products:
            if matches(p,field):
                vals=p[row_key] if isinstance(p[row_key],list) else [p[row_key]]
                for value in set(vals):counts[value]+=1
        fac[field]=[{'id':id,'label':label,'count':counts[id]} for id,label in options[field].items() if counts[id] or id in getattr(query,field)] if commercial else []
    for field in ('position_ids','location_ids'):fac[field]=[{'id':id,'label':label} for id,label in options[field].items()]
    pids={p['product_id'] for p in population}
    process_ids={l['process_id'] for pid in pids for pos in chosen[pid] for l in pos['layers'] if l.get('process_id')}
    costs=costing.published_origin_costs(db,process_ids) if cost_access else []
    lists=catalog.price_lists(db) if price_access else [];selected=next((l for l in lists if l['id']==query.price_list_id),None) if query.price_list_id else next(iter(lists),None)
    if query.price_list_id and price_access and not selected:raise ReportingError('Tabela de preço não disponível',code='invalid_price_list',status_code=422)
    now=datetime.now(ZoneInfo('America/Sao_Paulo'));prices=catalog.current_prices(db,selected['id'],now.date()) if selected else {}
    rows=[]
    for p in population:
        econ=value_product(p,chosen[p['product_id']],costs,prices.get(p['product_id']),can_cost=cost_access,can_price=price_access,price_currency=selected['currency'] if selected else None)
        row={**p,**econ}
        if not commercial:
            for k in ['modality_ids','modality_label','item_kind_id','item_kind_label','model_id','model_label','category_id','size','color','pack_qty']:row.pop(k,None)
        if not cost_access:
            for k in ['comparable_cost','comparable_sale','comparable_quantity','cost_quantity','contributions','margin']:row[k]=[] if k=='contributions' else Decimal(0) if k.endswith('quantity') else None
        rows.append(row)
    def sort_rows(items):
        key=query.sort.lstrip('-');field={'quantity':'quantity','cost':'cost_total','sale':'sale_total','name':'name'}[key]
        if key=='cost' and not cost_access or key=='sale' and not price_access:raise ReportingError('Ordenação sem permissão',code='forbidden',status_code=403)
        if key=='name':return sorted(items,key=lambda r:(r['name'].casefold(),r['product_id']),reverse=query.sort.startswith('-'))
        return sorted(items,key=lambda r:(r[field] is None,(-r[field] if query.sort.startswith('-') and r[field] is not None else r[field] or Decimal(0)),r['product_id']))
    rows=sort_rows(rows);totals=aggregate(rows,can_cost=cost_access,can_price=price_access)
    def make_groups(items,levels):
        if not levels:return []
        g=defaultdict(list)
        for r in items:g[r[{'item_kind':'item_kind_id','model':'model_id','modality':'modality_label'}[levels[0]]]].append(r)
        result=[]
        for id,members in g.items():
            label=members[0][{'item_kind':'item_kind_label','model':'model_label','modality':'modality_label'}[levels[0]]]
            result.append({'id':id,'label':label,'totals':aggregate(members,can_cost=cost_access,can_price=price_access),'product_ids':[r['product_id'] for r in members], 'children':make_groups(members,levels[1:])})
        return result
    groups=make_groups(rows,query.group_by)
    config=query.model_dump();filters={k:config[k] for k in ['q','modality_ids','item_kind_ids','model_ids','location_ids','position_ids','product_id','status']}
    fingerprint=sha256(json.dumps({'filters':filters,'ids':[r['product_id'] for r in sorted(rows,key=lambda r:r['product_id'])],'totals':serialize(totals)},sort_keys=True).encode()).hexdigest()
    return serialize({'rows':rows[query.offset:query.offset+query.limit],'total':len(rows),'offset':query.offset,'limit':query.limit,
        'groups':groups,'totals':totals,'facets':fac,'filters_applied':filters,'population_key':fingerprint,'generated_at':now.isoformat(),
        'capabilities':{'commercial':commercial,'cost':cost_access,'price':price_access},'price_list':selected,'price_lists':lists,'method':'ORIGIN_FIFO_MANAGEMENT_V1','currency':'BRL'})
