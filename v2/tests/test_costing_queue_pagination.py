"""Read-only costing discovery must not lose an older valid operation."""
import uuid

from app.costing.models import CostingCase, CostingVersion


def test_costing_queue_exact_and_global_pagination(admin_client, db):
    tag = "QUEUE-" + uuid.uuid4().hex[:8]
    rows = []
    for i in range(51):
        response = admin_client.post('/api/import-processes', json={'external_reference': f'{tag}-{i:03d}'})
        assert response.status_code == 201, response.text
        rows.append(response.json())
    oldest = rows[0]['id']
    case = CostingCase(import_process_id=oldest)
    db.add(case); db.flush()
    version = CostingVersion(case_id=case.id, version_number=1, kind='ESTIMATED', status='PUBLISHED', partial_coverage=True, included_total_brl=125)
    db.add(version); db.flush(); case.current_published_id = version.id; db.commit()

    default = admin_client.get('/api/costing/queue').json()
    assert len(default) == 50 and oldest not in [r['import_process_id'] for r in default]
    exact = admin_client.get('/api/costing/queue', params={'process_id': oldest}).json()
    assert len(exact) == 1 and exact[0]['id'] == case.id and exact[0]['included_total_brl'] == '125.0000'
    first = admin_client.get('/api/costing/queue-page', params={'q': tag}).json()
    second = admin_client.get('/api/costing/queue-page', params={'q': tag, 'offset': 50}).json()
    assert first['total'] == second['total'] == 51
    assert len(first['items']) == 50 and len(second['items']) == 1
    assert second['items'][0]['import_process_id'] == oldest
    assert not set(r['import_process_id'] for r in first['items']) & set(r['import_process_id'] for r in second['items'])
    for situation in ('ready', 'blocked'):
        filtered = admin_client.get('/api/costing/queue-page', params={'q': tag, 'situation': situation}).json()
        assert filtered['total'] == 1 and filtered['items'][0]['id'] == case.id
    empty = admin_client.get('/api/costing/queue-page', params={'q': tag, 'situation': 'empty'}).json()
    assert empty['total'] == 50
    assert admin_client.get('/api/costing/queue', params={'process_id': 999999999}).status_code == 404
    assert admin_client.get('/api/costing/queue', params={'limit': 101}).status_code == 422
    assert admin_client.get('/api/costing/queue-page', params={'offset': -1}).status_code == 422
    assert admin_client.get('/api/costing/queue-page', params={'situation': 'invalid'}).status_code == 422
    assert admin_client.get('/api/costing/queue-page', params={'q': tag+'%'}).json()['total'] == 0


def test_costing_queue_requires_authentication(client):
    for path in ('/api/costing/queue?process_id=1', '/api/costing/queue-page'):
        assert client.get(path).status_code == 401
