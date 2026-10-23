"""Managerial stock value; consumes public origin/cost/price DTOs only."""
from decimal import Decimal
ZERO=Decimal(0)

def value_product(product, positions, costs, price, *, can_cost, can_price, price_currency):
    qty=sum((p['quantity'] for p in positions),ZERO);cost_total=ZERO;cost_known=ZERO;cost_complete=ZERO
    comparable_cost=ZERO;comparable_sale=ZERO;comparable_qty=ZERO;eligible_qty=ZERO;contributions=[]
    price_ok=can_price and price and product['unit'] and price['unit']==product['unit'] and price_currency=='BRL'
    value=Decimal(price['amount']) if price_ok else None
    for pos in positions:
        eligible=pos['location']['regime']=='DOMESTIC' and pos['location']['active'] and product['active']
        if eligible:eligible_qty+=max(pos['quantity'],ZERO)
        if not can_cost:continue
        for layer in pos['layers']:
            count=layer['quantity'];matches=[c for c in costs if c['process_id']==layer.get('process_id') and c['product_id']==product['product_id'] and (
                layer.get('invoice_item_id') and c['invoice_item_id']==layer['invoice_item_id'] or
                not layer.get('invoice_item_id') and layer.get('shipment_item_id') and c['shipment_item_id']==layer['shipment_item_id'])]
            c=matches[0] if len(matches)==1 and product['unit'] and matches[0].get('unit')==product['unit'] else None
            if c and c['kind']!='ESTIMATED':
                subtotal=count*c['unit_brl'];cost_total+=subtotal;cost_known+=count
                if c['complete']:
                    cost_complete+=count
                    if eligible and price_ok:comparable_cost+=subtotal;comparable_sale+=count*value;comparable_qty+=count
                contributions.append({**c,'remaining_quantity':count,'subtotal':subtotal,'location':pos['location']['name'],'estimated':pos['estimated']})
    sale=eligible_qty*value if price_ok else None
    return {'quantity':qty,'eligible_quantity':eligible_qty,'cost_total':cost_total if can_cost and cost_known else None,
        'unit_cost':cost_total/qty if can_cost and qty>0 and cost_complete==qty else None,
        'cost_quantity':cost_complete,'price':value,'price_entry':price if can_price else None,'sale_total':sale,
        'price_quantity':eligible_qty if price_ok else ZERO,'comparable_cost':comparable_cost,'comparable_sale':comparable_sale,'comparable_quantity':comparable_qty,
        'margin':(comparable_sale-comparable_cost)/comparable_sale*100 if comparable_sale else None,
        'contributions':contributions,'estimated':any(p['estimated'] for p in positions),'origin_issue':any(not p['reconciled'] for p in positions)}

def aggregate(rows,*,can_cost=True,can_price=True):
    units={};covered={};priced={};comparable={}
    for r in rows:
        unit=r['unit'] or 'Não informada'
        for target,field in [(units,'quantity'),(covered,'cost_quantity'),(priced,'price_quantity'),(comparable,'comparable_quantity')]:target[unit]=target.get(unit,ZERO)+r[field]
    cc=sum((r['comparable_cost'] or ZERO for r in rows),ZERO);cs=sum((r['comparable_sale'] or ZERO for r in rows),ZERO)
    cost=[r['cost_total'] for r in rows if r['cost_total'] is not None];sale=[r['sale_total'] for r in rows if r['sale_total'] is not None]
    return {'sku_count':len(rows),'estimated':any(r['estimated'] for r in rows),'quantities':units,'cost_total':sum(cost,ZERO) if can_cost and (cost or not rows) else None,
        'sale_total':sum(sale,ZERO) if can_price and (sale or not rows) else None,'margin':(cs-cc)/cs*100 if cs and can_cost and can_price else None,
        'comparable_cost':cc if can_cost and can_price else None,'comparable_sale':cs if can_cost and can_price else None,
        'cost_skus':sum(1 for r in rows if r['quantity']>0 and r['cost_quantity']==r['quantity']) if can_cost else None,
        'price_skus':sum(1 for r in rows if r['eligible_quantity']>0 and r['price_quantity']==r['eligible_quantity']) if can_price else None,
        'cost_coverage':covered if can_cost else None,'price_coverage':priced if can_price else None,'comparable_coverage':comparable if can_cost and can_price else None}
