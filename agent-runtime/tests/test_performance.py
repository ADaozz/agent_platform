"""Compact polling must retain ownership and the existing full-session contract."""
import pytest
from fastapi.testclient import TestClient
from platform_app import domain as d, models as m, runtime as rt
from platform_app.main import app


@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(d,'DATA',tmp_path);d.init()
    m.save({'default':'test/model','models':{'test':{'base_url':'https://example.com/v1','api_key':'test-only','api':'chat_completions','models':{'model':{}}}}},0)
    rt.RUNTIMES.clear()
    yield TestClient(app)
    for runtime in rt.RUNTIMES.values():
        for service in runtime.artifact_services.values():service.close()
    rt.RUNTIMES.clear()


def test_sidebar_summary_never_reads_files_or_model_secrets(client,monkeypatch):
    created=client.post('/api/agent/sessions',json={'model_id':'test/model'}).json()
    record=d.get('session',created['id']);record['messages']=[{'role':'user','content':'Report title\n'+'body '*3000}];d.put('session',record)
    # Existing callers retain all detail and file information.
    full=client.get('/api/agent/sessions').json()[0]
    assert full['messages']==record['messages'] and 'output_files' in full
    def unexpected(*args,**kwargs):raise AssertionError('Summary reached a heavy detail path')
    monkeypatch.setattr(rt,'file_snapshot',unexpected);monkeypatch.setattr(m,'unseal',unexpected)
    response=client.get('/api/agent/sessions?summary=true')
    assert response.status_code==200
    summary=response.json()[0]
    assert summary['id']==created['id'] and summary['status']=='idle'
    assert summary['title']=='Report title'
    assert not {'config','model_snapshot','messages','documents','output_files'} & summary.keys()
    assert len(response.content)<1000


def test_summary_respects_owner_and_legacy_order(client,monkeypatch):
    for identity,owner in [('a','alice'),('b','bob'),('c','alice')]:
        d.put('session',dict(id=identity,owner_user_id=owner,model_id='test/model',status='idle',messages=[]))
    monkeypatch.setattr(rt.itam_bridge,'is_enabled',lambda:True)
    monkeypatch.setattr(rt.itam_bridge,'owner',lambda:'alice')
    assert [r['id'] for r in rt.sessions(summary=True)]==['c','a']
