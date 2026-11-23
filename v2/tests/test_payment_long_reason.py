import json
from datetime import date
from sqlalchemy import text


def test_long_override_reason_preserved_and_retry_does_not_duplicate(admin_client, db):
    c = admin_client
    supplier = c.post('/api/suppliers', json={'name':'QA long justification','country_code':'IT'}).json()
    reason = 'Ensaio isolado: justificativa completa de registro sem documento, com mais de sessenta e quatro caracteres.'
    body = dict(supplier_id=supplier['id'], amount='1000', currency='EUR', payment_date=date.today().isoformat(),
                register_without_document=True, reason_code=reason, external_reference='QA-LONG-REASON', idempotency_key='QA-LONG-REASON-RETRY')
    first = c.post('/api/payments', json=body)
    assert first.status_code == 200, first.text
    second = c.post('/api/payments', json=body)
    assert second.status_code == 200, second.text
    assert first.json()['id'] == second.json()['id']
    assert first.json()['amount_unallocated'] == '1000.00'
    row = db.execute(text("select reason_code,details from audit_log where entity_type='payment' and entity_id=:id and action='register' order by id desc limit 1"),{'id':str(first.json()['id'])}).one()
    assert row.reason_code == 'PAYMENT_REGISTER_WITHOUT_DOCUMENT'
    assert json.loads(row.details)['reason'] == reason
