"""Single-user loopback UI. Run on Delta and access through an SSH tunnel."""
import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from multigent.models import MODELS, DEFAULT_MODEL, validate_model

REPO = Path(__file__).resolve().parents[2]
TEXT_SUFFIXES = {'.sv', '.py', '.json', '.yaml', '.yml', '.md', '.txt', '.log', '.tcl', '.xdc', '.rpt', '.tsv', '.jsonl'}
OWNERS = {'contract_reviews': 'Contract Reviewer', 'architecture': 'Architect', 'rtl': 'RTL Generator', 'reference': 'Independent Testbench Generator',
          'tests': 'Independent Testbench Generator', 'verification': 'Verification', 'diagnostics': 'Debugger',
          'synthesis': 'Vivado', 'optimization': 'PPA Optimizer', 'reports': 'Reports',
          'specs': 'Request', 'state': 'Run state', 'logs': 'Logs', 'attempts': 'Earlier attempts'}


def read_json(path, default=None):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {} if default is None else default


def save_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2))
    temporary.replace(path)


def artifact_path(root, relative):
    candidate = root / relative
    parts = Path(relative).parts
    if (not parts or parts[0] not in OWNERS or any(p.startswith('.') or p in {'build', 'sim_build', '__pycache__'} for p in parts)
            or candidate.suffix not in TEXT_SUFFIXES or not candidate.resolve().is_relative_to(root.resolve())):
        raise ValueError('This file is outside the run artifact browser')
    if not candidate.is_file():
        raise FileNotFoundError(relative)
    return candidate


def artifacts(root):
    result = []
    for folder, owner in OWNERS.items():
        for base, dirs, files in os.walk(root/folder):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in {'build', 'sim_build', '__pycache__'} and not (Path(base)/d).is_symlink()]
            for name in sorted(files):
                relative = (Path(base)/name).relative_to(root).as_posix()
                try:
                    path = artifact_path(root, relative)
                    result.append({'path': relative, 'owner': owner, 'bytes': path.stat().st_size})
                except (ValueError, OSError):
                    pass
    return sorted(result, key=lambda item:item['path'])


class RunManager:
    def __init__(self, runs, repo=REPO, launcher=subprocess.Popen):
        self.runs = Path(runs).resolve()
        self.runs.mkdir(parents=True, exist_ok=True)
        self.repo = repo
        self.launcher = launcher
        self.lock = threading.Lock()
        self.processes = {}

    def root(self, run_id):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', run_id) or run_id in {'.', '..'}:
            raise ValueError('Invalid run identifier')
        path = self.runs/run_id
        if not path.resolve().is_relative_to(self.runs) or not path.is_dir():
            raise FileNotFoundError(run_id)
        return path

    def start(self, payload):
        request = payload.get('request', '')
        if not isinstance(request, str) or not request.strip() or len(request)>30000:
            raise ValueError('Enter a request between 1 and 30,000 characters')
        model = validate_model(payload.get('model', DEFAULT_MODEL))
        verification_only = payload.get('verification_only', True)
        if not isinstance(verification_only, bool):
            raise ValueError('verification_only must be true or false')
        with self.lock:
            if any(p.poll() is None for p in self.processes.values()):
                raise ValueError('A run is already working. Wait for it to finish before starting another.')
            run_id = datetime.now(timezone.utc).strftime('run-%Y%m%d-%H%M%S-')+secrets.token_hex(3)
            root = self.runs/run_id
            root.mkdir()
            (root/'logs').mkdir()
            metadata = {'run_id': run_id, 'request': request.strip(), 'model': model,
                        'created': datetime.now(timezone.utc).isoformat(), 'status': 'RUNNING',
                        'verification_only': verification_only}
            save_json(root/'ui_run.json', metadata)
            env = dict(os.environ, NPU_WORKSPACE_ROOT=str(root), NPU_AGENT_MODEL=model,
                       NPU_AGENT_API_MODE='responses')
            command = [sys.executable, '-u', '-m', 'multigent.orchestration.graph',
                       '--request', request.strip(), '--run-id', run_id, '--model', model]
            if verification_only:
                command.insert(4, '--verification-only')
            try:
                with (root/'logs'/'pipeline.log').open('w') as log:
                    process = self.launcher(command, cwd=self.repo, env=env, stdout=log,
                                            stderr=subprocess.STDOUT, start_new_session=True)
            except Exception as exc:
                metadata.update(status='FAILED', error=str(exc))
                save_json(root/'ui_run.json', metadata)
                raise
            self.processes[run_id] = process
            threading.Thread(target=self._watch, args=(run_id,process), daemon=True).start()
            return metadata

    def _watch(self, run_id, process):
        code = process.wait()
        root = self.root(run_id)
        metadata = read_json(root/'ui_run.json')
        final = read_json(root/'reports'/'final.json')
        metadata.update(status=final.get('status', 'SUCCESS' if code == 0 else 'FAILED'), exit_code=code)
        save_json(root/'ui_run.json', metadata)

    def listing(self):
        result = []
        for root in sorted(self.runs.iterdir(), reverse=True):
            if not root.is_dir() or root.is_symlink():
                continue
            metadata = read_json(root/'ui_run.json')
            if not metadata:
                state = read_json(root/'state'/'latest.json')
                if not state:
                    continue
                metadata = {'run_id': root.name, 'request': state.get('user_request',''),
                            'model': state.get('model', 'Not recorded'), 'status': state.get('status','UNKNOWN')}
            if metadata.get('status') == 'RUNNING' and root.name not in self.processes:
                metadata = {**metadata, 'status': 'MONITOR_UNAVAILABLE'}
            result.append(metadata)
        return result

    def status(self, run_id):
        root = self.root(run_id)
        metadata = read_json(root/'ui_run.json')
        state = read_json(root/'state'/'latest.json')
        events = []
        try:
            for line in (root/'state'/'events.jsonl').read_text().splitlines():
                try:
                    events.append(json.loads(line))
                except ValueError:
                    pass  # The writer may currently be appending this last line.
        except OSError:
            pass
        process = self.processes.get(run_id)
        running = process is not None and process.poll() is None
        status = metadata.get('status', state.get('status','UNKNOWN'))
        if status == 'RUNNING' and not running:
            status = 'MONITOR_UNAVAILABLE' if process is None else state.get('status','FINISHING')
        return {'run_id': run_id, 'request': metadata.get('request',state.get('user_request','')),
                'model': metadata.get('model',state.get('model','Not recorded')),
                'status': status, 'running': running, 'events': events[-500:],
                'history': state.get('history',[])[-100:], 'errors': state.get('errors',[])[-5:],
                'verification_status': state.get('verification_status'),
                'files': artifacts(root)}


def handler(manager, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, body, content_type='application/json'):
            data = json.dumps(body).encode() if content_type=='application/json' else body.encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type+'; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def authorized(self):
            return secrets.compare_digest(self.headers.get('X-UI-Token',''), token)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == '/':
                return self.send(200, (Path(__file__).parent/'index.html').read_text(), 'text/html')
            if not self.authorized():
                return self.send(403, {'error':'Open the private link printed by the UI server.'})
            try:
                query = parse_qs(url.query)
                if url.path == '/api/config':
                    return self.send(200, {'models': MODELS, 'default_model':DEFAULT_MODEL})
                if url.path == '/api/runs':
                    return self.send(200, manager.listing())
                run_id = query.get('run',[''])[0]
                if url.path == '/api/status':
                    return self.send(200, manager.status(run_id))
                if url.path == '/api/file':
                    path = artifact_path(manager.root(run_id),query.get('path',[''])[0])
                    with path.open('r', errors='replace') as stream:
                        content = stream.read(2_000_001)
                    return self.send(200, {'content':content[:2_000_000], 'truncated':len(content)>2_000_000})
                self.send(404, {'error':'Not found'})
            except (ValueError, FileNotFoundError) as exc:
                self.send(400, {'error':str(exc)})

        def do_POST(self):
            if not self.authorized():
                return self.send(403, {'error':'Private session token required'})
            if self.path != '/api/start':
                return self.send(404, {'error':'Not found'})
            try:
                length = int(self.headers.get('Content-Length','0'))
                if not 0 < length <= 100000:
                    raise ValueError('Invalid request size')
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError('Request must be an object')
                self.send(201, manager.start(payload))
            except (ValueError, TypeError) as exc:
                self.send(400, {'error':str(exc)})
            except Exception:
                self.send(500, {'error':'Could not launch the pipeline. Check the server environment.'})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--runs-dir',type=Path,default=REPO/'multigent'/'runs')
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(REPO/'.env')
    token = secrets.token_urlsafe(32)
    manager = RunManager(args.runs_dir)
    server = ThreadingHTTPServer(('127.0.0.1',args.port),handler(manager,token))
    print(f'Open http://localhost:{args.port}/#{token}',flush=True)
    print('For Delta: forward this port over SSH. Keep this server running to monitor active runs.',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
