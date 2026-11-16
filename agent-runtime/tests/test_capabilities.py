import pytest
from fastapi.testclient import TestClient
from platform_app import domain as d
from platform_app.main import app

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(d, 'DATA', tmp_path); d.init()
    return TestClient(app)

def test_capabilities_roundtrip(client):
    caps = client.get('/api/platform/capabilities').json()
    assert caps['editable'] and any(t['name'] == 'start_background_task' for t in caps['core_tools'])
    skills = {s['id']: s for s in caps['skills']}
    print(sorted(skills))
    body = {'revision': caps['revision'], 'core_tools': {'web_search': False}, 'skill_bindings': {next(iter(skills)): False}}
    out = client.put('/api/platform/capabilities', json=body)
    assert out.status_code == 200, out.text
    out = out.json()
    assert not next(t for t in out['core_tools'] if t['name'] == 'web_search')['enabled']
    assert not next(s for s in out['skills'] if s['id'] == next(iter(skills)))['enabled']
    assert client.put('/api/platform/capabilities', json=body).status_code == 409
    assert client.put('/api/platform/capabilities', json={'revision': out['revision'], 'core_tools': {'nope': True}}).status_code == 422
