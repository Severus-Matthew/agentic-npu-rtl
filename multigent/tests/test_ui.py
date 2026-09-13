import json
import threading
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import pytest
from multigent.models import MODELS, validate_model
from multigent.ui.server import RunManager, artifact_path, artifacts, handler
from multigent.orchestration.events import emit


@pytest.mark.parametrize('model', list(MODELS))
def test_every_agent_uses_selected_model_after_import(monkeypatch,model):
    from multigent.agents.architect import ArchitectAgent
    from multigent.agents.rtl_generator import RTLGeneratorAgent
    from multigent.agents.verifier import VerifierAgent
    from multigent.agents.debugger import DebuggerAgent
    from multigent.agents.ppa_optimizer import PPAOptimizerAgent
    monkeypatch.setenv('NPU_AGENT_MODEL',model)
    for role in (ArchitectAgent,RTLGeneratorAgent,VerifierAgent,DebuggerAgent,PPAOptimizerAgent):
        assert role().config.model==model


def test_guard_emits_start_before_role_and_finish_after_artifacts(tmp_path,monkeypatch):
    from multigent.orchestration import artifacts as module
    monkeypatch.setattr(module,'WORKSPACE_ROOT',tmp_path)
    def role(state):
        event=json.loads((tmp_path/'state'/'events.jsonl').read_text())
        assert event['phase']=='started'
        return {'status':'DONE'}
    module.guarded('debugger',role)({'history':[]})
    events=[json.loads(line) for line in (tmp_path/'state'/'events.jsonl').read_text().splitlines()]
    assert [e['phase'] for e in events]==['started','finished']
    assert (tmp_path/'state'/'latest.json').exists()


@pytest.mark.parametrize('model', list(MODELS))
def test_ui_launch_freezes_model_and_preserves_general_request(tmp_path,model):
    released=threading.Event()
    captured={}
    class Process:
        def poll(self): return None if not released.is_set() else 2
        def wait(self): released.wait(5); return 2
    def launch(command, **kwargs):
        captured.update(command=command,**kwargs)
        return Process()
    manager=RunManager(tmp_path,launcher=launch)
    result=manager.start({'request':'Design a saturating signed vector reducer', 'model':model})
    try:
        assert captured['env']['NPU_AGENT_MODEL']==model
        assert captured['env']['NPU_WORKSPACE_ROOT']==str(tmp_path/result['run_id'])
        assert captured['command'][-1]==model
        assert 'Design a saturating signed vector reducer' in captured['command']
        with pytest.raises(ValueError,match='already working'):
            manager.start({'request':'another design','model':model})
        assert manager.status(result['run_id'])['running']
    finally: released.set()


def test_ui_rejects_unknown_model_and_blank_request(tmp_path):
    manager=RunManager(tmp_path)
    with pytest.raises(ValueError): manager.start({'request':' '})
    with pytest.raises(ValueError): manager.start({'request':'adder','model':'unknown'})
    assert list(tmp_path.iterdir())==[]


def test_ui_file_browser_cannot_escape_or_read_secrets(tmp_path):
    run=tmp_path/'run';run.mkdir();(run/'rtl').mkdir()
    (run/'rtl'/'block.sv').write_text('module block; endmodule')
    secret=tmp_path/'secret.json';secret.write_text('private')
    (run/'rtl'/'leak.json').symlink_to(secret)
    for name in ('../secret.json','rtl/leak.json','.env','rtl/../../secret.json'):
        with pytest.raises((ValueError,FileNotFoundError)):artifact_path(run,name)
    assert [f['path'] for f in artifacts(run)]==['rtl/block.sv']


def test_ui_reads_live_events_and_artifacts_before_run_finishes(tmp_path):
    manager=RunManager(tmp_path);root=tmp_path/'example';root.mkdir()
    (root/'architecture').mkdir();(root/'architecture'/'contract.yaml').write_text('operation: reduce')
    emit(root,'architect','started')
    emit(root,'architect','finished',history=[{'status':'READY'}])
    emit(root,'rtl_generator','started')
    with (root/'state'/'events.jsonl').open('a') as stream:stream.write('{partial')
    data=manager.status('example')
    assert len(data['events'])==3
    assert data['events'][-1]['stage']=='rtl_generator'
    assert data['files'][0]['owner']=='Architect'


def test_ui_http_requires_token_and_serves_artifact_as_data(tmp_path):
    manager=RunManager(tmp_path);root=tmp_path/'example';(root/'tests').mkdir(parents=True)
    (root/'tests'/'test.py').write_text('<script>alert(1)</script>')
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(manager,'test-token'))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    base=f'http://127.0.0.1:{server.server_port}'
    try:
        with pytest.raises(HTTPError) as exc:urlopen(base+'/api/runs')
        assert exc.value.code==403
        req=Request(base+'/api/file?run=example&path=tests/test.py',headers={'X-UI-Token':'test-token'})
        with urlopen(req) as response:
            assert response.headers['Content-Type'].startswith('application/json')
            assert json.load(response)['content']=='<script>alert(1)</script>'
        req=Request(base+'/api/start',data=b'{}',headers={'Content-Type':'application/json'})
        with pytest.raises(HTTPError) as exc:urlopen(req)
        assert exc.value.code==403
    finally:server.shutdown();server.server_close();thread.join()
