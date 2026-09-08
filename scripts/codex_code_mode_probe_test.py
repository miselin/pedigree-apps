import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


PROBE = Path(__file__).resolve().parents[1] / "language-ports/codex-code-mode-host/probe.c"
# This peer validates the qualifier only. It never executes JavaScript.
FIXTURE = r'''
import json, os, pathlib, struct, sys, time
mode = pathlib.Path(sys.argv[0]).stem
home = os.environ['HOME']
assert home.startswith('/tmp/codex-code-mode-qualify-')
assert os.environ['CODEX_HOME'] == home == os.environ['TMPDIR']
assert not any(x in os.environ for x in ('OPENAI_API_KEY', 'CODEX_API_KEY', 'ANTHROPIC_API_KEY'))
assert sys.argv[1:] == ['--listen', 'stdio']
print('FIXTURE_HOME=' + home, file=sys.stderr, flush=True)
print('FIXTURE_PID=' + str(os.getpid()), file=sys.stderr, flush=True)
def read():
    header = sys.stdin.buffer.read(4)
    if not header: return None
    assert len(header) == 4
    size, = struct.unpack('<I', header)
    assert 0 < size < 65536
    body = sys.stdin.buffer.read(size)
    assert len(body) == size
    return json.loads(body)
def send(value, raw=None):
    payload = json.dumps(value).encode() if raw is None else raw
    frame = struct.pack('<I', len(payload)) + payload
    if mode == 'fragmented':
        for i in range(0, len(frame), 3):
            sys.stdout.buffer.write(frame[i:i+3]); sys.stdout.buffer.flush()
    else:
        sys.stdout.buffer.write(frame); sys.stdout.buffer.flush()
def response(id, value):
    send({'type':'operation/response', 'id':id, 'result':{'status':'ok','value':value}})
def runtime(cell, kind='Result', text=None, error=None):
    value = {'cell_id':str(cell), 'content_items':[] if text is None else [{'type':'input_text','text':text}], 'code_mode_host_duration_ns':1000}
    if kind == 'Result': value['error_text'] = error
    return {kind:value}
def close(cell):
    if mode != 'unclosed': send({'type':'cell/closed','sessionId':session,'cellId':str(cell)})
hello = read()
assert hello == {'type':'connection/hello','supportedVersions':[1],'requiredCapabilities':['session-cell-execution-resource-limits'],'optionalCapabilities':[]}
ready = {'type':'connection/ready','selectedVersion':1,'capabilities':hello['requiredCapabilities']}
if mode == 'version': ready['selectedVersion'] = 2
if mode == 'oversize':
    sys.stdout.buffer.write(struct.pack('<I', 65536)); sys.stdout.buffer.flush(); time.sleep(10); sys.exit(0)
if mode == 'hang':
    sys.stdout.buffer.write(b'\x05\x00'); sys.stdout.buffer.flush(); time.sleep(10); sys.exit(0)
if mode == 'duplicate':
    send(None, b'{"type":"connection/ready","selectedVersion":2,"selected\\u0056ersion":1,"capabilities":["session-cell-execution-resource-limits"]}')
elif mode == 'malformed': send(None, b'{"type":"unterminated')
else: send(ready)
cell = 0
session = 'pedigree-qualification'
deferred = None
while True:
    message = read()
    if message is None: sys.exit(9 if mode == 'exit' else 0)
    assert message['type'] == 'operation/request'
    id, request = message['id'], message['request']
    assert request['sessionId'] == session
    method = request['method']
    if method == 'session/open':
        assert request['cellExecutionLimits'] == {'maxHeapSizeBytes':67108864,'maxYieldTimeMs':1000}
        response(id, {'type':'session/ready','sessionId':session})
    elif method == 'session/execute':
        cell += 1
        execution = request['request']
        assert execution['tool_call_id'] == 'qualify-' + str(cell)
        sources = {
            1: "store('answer', 6 * 7); text(load('answer'));",
            2: "const r = await tools.echo({value: await Promise.resolve(load('answer'))}); text(r.answer);",
            3: "throw new Error('qualify-error');",
            4: "text(load('answer') + 1);",
            5: "await new Promise(() => {});",
            6: "text(load('answer') * 2);",
        }
        assert execution['source'] == sources[cell]
        response(id + (1 if mode == 'correlation' else 0), {'type':'execution/started','cellId':str(cell)})
        if cell == 2:
            assert execution['enabled_tools'][0]['tool_name'] == {'name':'echo','namespace':None}
            if mode != 'skip-tool':
                send({'type':'delegate/request','id':71,'sessionId':session,'request':{'type':'tool/invoke','invocation':{
                    'cell_id':'2','runtime_tool_call_id':'tool-1','tool_name':{'name':'echo','namespace':None},
                    'tool_kind':'function','input':{'value':41 if mode == 'tool' else 42}}}})
                assert read() == {'type':'delegate/response','id':71,'result':{'status':'ok','value':{'type':'tool/result','result':{'answer':43}}}}
        elif cell != 2: assert execution['enabled_tools'] == []
        text = {1:'41' if mode == 'arithmetic' else '42', 2:'43', 4:'43', 6:'84'}.get(cell)
        error = ('unrelated error' if mode == 'exception' else 'Error: qualify-error') if cell == 3 else None
        result = runtime(cell, 'Yielded' if cell == 5 else 'Result', text, error)
        if mode in ('yield', 'yield-text', 'repeat-text') and cell == 1:
            deferred = runtime(cell) if mode == 'yield-text' else result
            result = runtime(cell, 'Yielded', None if mode == 'yield' else text)
        send({'type':'execute/initialResponse','id':id,'result':{'status':'ok','value':result}})
        if cell != 5 and deferred is None: close(cell)
    elif method == 'session/wait':
        assert request['request']['cell_id'] == str(cell)
        result = deferred or runtime(cell, 'Yielded')
        response(id, {'type':'wait/completed','outcome':{'LiveCell':result}})
        if deferred is not None: deferred = None; close(cell)
    elif method == 'session/terminate':
        assert cell == 5 and request['cellId'] == '5'
        response(id, {'type':'wait/completed','outcome':{'LiveCell':runtime(cell, 'Terminated')}})
        close(cell)
    elif method == 'session/shutdown':
        assert cell == 6
        response(id, {'type':'session/closed','sessionId':session})
        if mode == 'extra': send({'type':'unexpected-after-shutdown'}); sys.exit(0)
    else: raise AssertionError(method)
'''


class CodeModeProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="codex-code-mode-test-")
        cls.directory = Path(cls.temporary.name)
        cls.probe = cls.directory / "probe"
        subprocess.run(shlex.split(os.environ.get("CC", "cc")) + ["-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", str(PROBE), "-o", str(cls.probe)], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def run_peer(self, mode, success=False, timeout=2000):
        peer = self.directory / mode
        peer.write_text(f"#!{sys.executable}\n" + FIXTURE)
        peer.chmod(0o755)
        env = dict(os.environ, CODEX_CODE_MODE_QUALIFY_TIMEOUT_MS=str(timeout), OPENAI_API_KEY="must-not-be-inherited")
        result = subprocess.run([str(self.probe), str(peer)], text=True, capture_output=True, env=env, timeout=6)
        log = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, success, log)
        self.assertEqual("CODEX-CODE-MODE: PASS all (9 checks)" in result.stdout, success, log)
        for line in result.stderr.splitlines():
            if line.startswith("FIXTURE_HOME="):
                self.assertFalse(Path(line.split("=", 1)[1]).exists(), log)
            if line.startswith("FIXTURE_PID="):
                with self.assertRaises(ProcessLookupError): os.kill(int(line.split("=", 1)[1]), 0)
        return log

    def test_complete_framed_protocol(self): self.run_peer("good", True)
    def test_fragmented_frames(self): self.run_peer("fragmented", True)
    def test_completed_calculation_can_yield(self): self.run_peer("yield", True)
    def test_yield_can_deliver_output(self): self.run_peer("yield-text", True)
    def test_repeated_output_across_yields_is_rejected(self): self.run_peer("repeat-text")
    def test_wrong_arithmetic(self): self.run_peer("arithmetic")
    def test_wrong_tool_argument(self): self.run_peer("tool")
    def test_result_without_callback_is_rejected(self): self.run_peer("skip-tool")
    def test_wrong_request_id(self): self.run_peer("correlation")
    def test_unrelated_exception(self): self.run_peer("exception")
    def test_all_cells_must_close(self): self.run_peer("unclosed")
    def test_nonzero_host_exit(self): self.run_peer("exit")
    def test_queued_output_after_clean_exit_is_rejected(self): self.run_peer("extra")
    def test_wrong_negotiated_version(self): self.run_peer("version")
    def test_oversized_frame_is_rejected(self): self.run_peer("oversize")
    def test_duplicate_decoded_key(self): self.run_peer("duplicate")
    def test_truncated_json_is_rejected(self): self.run_peer("malformed")
    def test_partial_frame_deadline_reaps_and_cleans(self):
        self.assertIn("stage=handshake", self.run_peer("hang", timeout=200))


if __name__ == "__main__":
    unittest.main()
