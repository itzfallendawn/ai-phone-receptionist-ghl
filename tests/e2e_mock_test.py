"""End-to-end test for the AI Phone Receptionist against a MOCK GoHighLevel API.

No real GoHighLevel account is used. The script:
  1. starts a small mock GoHighLevel API on this machine,
  2. imports a temporary copy of the workflow into your n8n (GHL URLs pointed at the mock, fake config values),
  3. sends six VAPI-style tool calls (three failure cases, three normal cases),
  4. prints every reply plus every request the workflow made, then deletes the temporary copy.

Requirements: Python 3.9+, a running n8n with the public API enabled.
Environment:
  N8N_URL      default http://localhost:5678
  N8N_API_KEY  your n8n API key (Settings > n8n API)
  MOCK_HOST    how n8n reaches this machine; default host.docker.internal (n8n in Docker).
               Use 127.0.0.1 if n8n runs directly on this machine.
Usage: python tests/e2e_mock_test.py
"""
import copy, json, os, threading, time, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

N8N = os.environ.get('N8N_URL', 'http://localhost:5678').rstrip('/')
KEY = os.environ.get('N8N_API_KEY', '')
MOCK_PORT = 8765
MOCK = f"http://{os.environ.get('MOCK_HOST', 'host.docker.internal')}:{MOCK_PORT}"
WORKFLOW = Path(__file__).resolve().parent.parent / 'workflow' / 'ai-phone-receptionist-ghl.json'
KNOWN_PHONE = '+15551112222'   # the mock "already knows" this caller
LOG = []
MODE = {'fail': False}         # when True the mock rejects every request (401)


class MockGHL(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        LOG.append(('GET', self.path, None))
        if MODE['fail']:
            return self._send(401, {'message': 'Invalid JWT'})
        if '/free-slots' in self.path:
            return self._send(200, {
                '2030-01-15': {'slots': ['2030-01-15T10:00:00-05:00', '2030-01-15T11:00:00-05:00', '2030-01-15T14:30:00-05:00']},
                '2030-01-16': {'slots': ['2030-01-16T09:00:00-05:00']},
                'traceId': 'mock-trace'})
        if self.path.startswith('/contacts/'):
            known = KNOWN_PHONE.replace('+', '%2B') in self.path
            found = [{'id': 'existing-contact-1'}] if known else []
            return self._send(200, {'contacts': found, 'meta': {'total': len(found)}})
        return self._send(404, {'message': 'not mocked'})

    def do_POST(self):
        length = int(self.headers.get('Content-Length') or 0)
        body = json.loads(self.rfile.read(length) or b'{}')
        LOG.append(('POST', self.path, body))
        if MODE['fail']:
            return self._send(401, {'message': 'Invalid JWT'})
        if self.path.rstrip('/') == '/contacts':
            return self._send(201, {'contact': {'id': 'new-contact-1'}})
        if self.path.startswith('/calendars/events/appointments'):
            return self._send(201, {'id': 'appt-1', 'appointmentStatus': 'confirmed'})
        if '/notes' in self.path:
            return self._send(201, {'note': {'id': 'note-1'}})
        return self._send(404, {'message': 'not mocked'})


def api(method, path, body=None):
    req = urllib.request.Request(N8N + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={'X-N8N-API-KEY': KEY, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode()
        return json.loads(text) if text else {}


def tool_call(path, name, args, phone):
    payload = {'message': {'toolCallList': [{'id': f'tc-{name}', 'function': {'name': name, 'arguments': args}}]},
               'call': {'customer': {'number': phone}}}
    req = urllib.request.Request(f'{N8N}/webhook/{path}', method='POST', data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())['results'][0]['result']


def main():
    if not KEY:
        raise SystemExit('Set N8N_API_KEY first.')
    server = ThreadingHTTPServer(('127.0.0.1', MOCK_PORT), MockGHL)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    wf = copy.deepcopy(json.loads(WORKFLOW.read_text(encoding='utf-8')))
    path = 'receptionist-e2e-test'
    for node in wf['nodes']:
        params = node.get('parameters', {})
        if node['name'] == 'VAPI Webhook':
            params['path'] = path
        if node['name'] == 'Config':
            fake = {'calendarId': 'mock-calendar', 'locationId': 'mock-location', 'testPhone': '+15550000000',
                    'timezone': 'America/New_York', 'ghlApiKey': 'mock-key'}
            for a in params['assignments']['assignments']:
                a['value'] = fake.get(a['name'], a['value'])
        if 'url' in params:
            params['url'] = params['url'].replace('https://services.leadconnectorhq.com', MOCK)

    created = api('POST', '/api/v1/workflows', {'name': 'TEST receptionist e2e (temporary)', 'nodes': wf['nodes'],
                                                'connections': wf['connections'], 'settings': wf.get('settings', {})})
    wid = created['id']
    results = []
    try:
        api('POST', f'/api/v1/workflows/{wid}/activate')
        time.sleep(2)
        when = '2030-01-15T15:00:00Z'
        results.append(('Unknown tool name', tool_call(path, 'transfer_call', {}, '+15553334444')))
        MODE['fail'] = True
        results.append(('Check calendar, GoHighLevel rejects', tool_call(path, 'check_calendar', {'requested_time': when}, '+15553334444')))
        results.append(('Book, GoHighLevel rejects', tool_call(path, 'book_calendar', {'name': 'Test Caller', 'requested_time': when}, '+15553334444')))
        MODE['fail'] = False
        LOG.clear()
        results.append(('Check calendar', tool_call(path, 'check_calendar', {'requested_time': '2030-01-15T09:00:00Z'}, '+15553334444')))
        results.append(('Book, new caller', tool_call(path, 'book_calendar', {'name': 'Jamie Rivera', 'requested_time': when, 'reason': 'Roof inspection'}, '+15553334444')))
        time.sleep(2)
        results.append(('Book, returning caller', tool_call(path, 'book_calendar', {'name': 'Pat Lee', 'requested_time': '2030-01-16T14:00:00Z', 'reason': 'Follow-up'}, KNOWN_PHONE)))
        time.sleep(3)
    finally:
        try:
            api('POST', f'/api/v1/workflows/{wid}/deactivate')
        finally:
            api('DELETE', f'/api/v1/workflows/{wid}')
            server.shutdown()

    print('REPLIES')
    for label, reply in results:
        print(f'- {label}: "{reply}"')
    print('\nREQUESTS TO THE MOCK GOHIGHLEVEL API (normal cases)')
    for method, p, body in LOG:
        print(f'- {method} {p}' + (f'\n  {json.dumps(body)}' if body else ''))


if __name__ == '__main__':
    main()
