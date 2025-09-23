import time
from fastapi.testclient import TestClient
from apps.api.app.main import app


client = TestClient(app)


def _auth():
    return client.post('/auth/magic', json={'email': 'demo@local.test'}).json()['token']


def test_seeded_recs_under_soft_threshold():
    token = _auth()
    starts = time.time()
    for _ in range(10):
        r = client.get('/recommendations', params={'for': 'ross', 'seed': 123, 'intent': 'default'}, headers={'Authorization': f'Bearer {token}'})
        assert r.status_code == 200
    avg = (time.time() - starts) / 10.0
    assert avg < 0.6

