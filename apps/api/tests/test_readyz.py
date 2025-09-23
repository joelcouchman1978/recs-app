from fastapi.testclient import TestClient
from apps.api.app.main import app

client = TestClient(app)


def test_readyz_endpoint_schema():
    r = client.get('/readyz')
    assert r.status_code == 200
    body = r.json()
    assert 'status' in body and 'checks' in body

