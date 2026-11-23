from app.costing.commands import _sku_rollup


def line(value):
    return dict(product_id=1, sku_snapshot='QA-ABSENCE', invoice_item_id=1,
                shipment_item_id=1, qty='10', merchandise_brl=value)


def test_missing_merchandise_and_failed_allocation_are_not_zero():
    components = [dict(included=False, source_kind='TAX_LINE', component_type='II',
                       amount_brl='1200', status='missing_basis', allocations=[])]
    row = _sku_rollup([line(None)], components)[0]
    assert row['merchandise_brl'] is None
    assert row['tax_brl'] is None
    assert row['total_brl'] is None and row['unit_brl'] is None
    assert row['qty'] == '10'


def test_known_zero_remains_zero():
    row = _sku_rollup([line('0')], [dict(included=True, source_kind='INVOICE', component_type='MERCADORIA',
        status='OK', allocations=[dict(invoice_item_id=1,shipment_item_id=1,amount_brl='0')])])[0]
    assert row['merchandise_brl'] == '0.00'
    assert row['total_brl'] == '0.00'


def test_one_missing_line_does_not_zero_the_other_product():
    known = {**line('100'), 'product_id':2, 'sku_snapshot':'QA-KNOWN', 'invoice_item_id':2}
    rows = _sku_rollup([line(None), known], [dict(included=True, source_kind='INVOICE',component_type='MERCADORIA',status='OK',
        allocations=[dict(invoice_item_id=2,shipment_item_id=1,amount_brl='100')])])
    assert rows[0]['total_brl'] is None
    assert rows[1]['total_brl'] == '100.00'
