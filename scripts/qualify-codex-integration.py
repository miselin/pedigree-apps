#!/usr/bin/env python3
"""Exercise Codex and its Code Mode host against a local scripted provider."""

import argparse
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time


LIMIT = 4 * 1024 * 1024
CALL_ID = "pedigree-code-mode-probe"
PROOF = "CODEX_CODE_MODE_COMMAND_OK\n"
FINAL = "CODEX_CODE_MODE_INTEGRATION_OK"


def file_hash(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def completed(identifier):
    return {"type": "response.completed", "response": {
        "id": identifier,
        "usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
    }}


def tool_output(request):
    outputs = [item for item in request.get("input", [])
               if item.get("type") == "custom_tool_call_output"
               and item.get("call_id") == CALL_ID]
    if len(outputs) != 1:
        raise ValueError("expected exactly one Code Mode result")
    output = outputs[0].get("output")
    if (not isinstance(output, list) or len(output) != 2
            or any(item.get("type") != "input_text" for item in output)
            or not output[0].get("text", "").startswith("Script completed\n")):
        raise ValueError("unexpected Code Mode output shape")
    text = output[1].get("text", "")
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("Code Mode result is not an object")
    command = value.get("command")
    if (type(value.get("calculation")) is not int or value["calculation"] != 42
            or not isinstance(command, dict)
            or type(command.get("exit_code")) is not int or command["exit_code"] != 0
            or command.get("output") != PROOF or "session_id" in command):
        raise ValueError("Code Mode did not return completed arithmetic and command results")
    return text


def advertised_exec(request):
    matches = []
    for tool in request.get("tools", []):
        if tool.get("name") == "exec" and tool.get("type") == "custom":
            matches.append(None)
        elif tool.get("type") == "namespace" and tool.get("name") == "functions":
            for child in tool.get("tools", []):
                if child.get("name") == "exec" and child.get("type") == "custom":
                    matches.append("functions")
    if len(matches) != 1:
        raise ValueError("expected exactly one advertised Code Mode exec tool")
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex", type=Path, required=True,
                        help="actual Codex executable, with its host alongside it")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args()
    if not 10 <= args.timeout <= 1800:
        parser.error("timeout must be between 10 and 1800 seconds")
    binary = args.codex.resolve(strict=True)
    host = binary.with_name("codex-code-mode-host")
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    requests, errors = [], []
    lock = threading.Lock()
    result = {"status": "fail", "scope": "local scripted provider; no authentication or model inference",
              "codex_sha256": file_hash(binary),
              "host_sha256": file_hash(host) if host.is_file() else None}

    with tempfile.TemporaryDirectory(prefix="codex-integration-") as temporary:
        home = Path(temporary)
        project = home / "project"
        project.mkdir()
        proof = project / "proof.txt"
        patch = "*** Begin Patch\n*** Add File: proof.txt\n+" + PROOF + "*** End Patch\n"
        code = (
            "const patchResult = await tools.apply_patch(" + json.dumps(patch) + ");\n"
            "const command = await tools.exec_command({cmd: 'cat proof.txt', "
            "tty: false, login: false, shell: '/bin/sh', yield_time_ms: 1000, max_output_tokens: 100});\n"
            "text(JSON.stringify({calculation: await Promise.resolve(6 * 7), patchResult, command}));"
        )

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(10)

            def log_message(self, *_):
                pass

            def do_POST(self):
                try:
                    if self.path != "/v1/responses":
                        raise ValueError("unexpected provider endpoint: " + self.path)
                    if self.headers.get("Authorization"):
                        raise ValueError("unexpected credentials in isolated provider request")
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 0 < length <= LIMIT or self.headers.get("Content-Encoding"):
                        raise ValueError("unsupported provider request encoding or size")
                    raw = self.rfile.read(length)
                    if len(raw) != length:
                        raise ValueError("incomplete provider request")
                    request = json.loads(raw)
                    with lock:
                        requests.append(request)
                        number = len(requests)
                    if number == 1:
                        namespace = advertised_exec(request)
                        call = {"type": "custom_tool_call", "call_id": CALL_ID,
                                "name": "exec", "input": code}
                        if namespace is not None:
                            call["namespace"] = namespace
                        events = [
                            {"type": "response.created", "response": {"id": "probe-1"}},
                            {"type": "response.output_item.done", "item": call},
                            completed("probe-1"),
                        ]
                    elif number == 2:
                        tool_output(request)
                        if proof.read_text() != PROOF:
                            raise ValueError("expected file was not written by the delegated tool")
                        events = [
                            {"type": "response.output_item.done", "item": {
                                "type": "message", "role": "assistant", "id": "probe-message",
                                "content": [{"type": "output_text", "text": FINAL}],
                            }},
                            completed("probe-2"),
                        ]
                    else:
                        raise ValueError("unexpected extra provider request")
                    payload = "".join("event: " + event["type"] + "\ndata: " + json.dumps(event)
                                      + "\n\n" for event in events).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                except Exception as error:
                    with lock:
                        errors.append(str(error))
                    self.send_error(400, "qualification fixture rejected request")

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        # Join bounded request handlers before examining their final verdicts.
        server.daemon_threads = False
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        (home / "config.toml").write_text(
            'model = "gpt-5.5"\nmodel_provider = "qualification"\n'
            'approval_policy = "never"\nsandbox_mode = "danger-full-access"\n'
            'check_for_update_on_startup = false\nweb_search = "disabled"\n'
            '[analytics]\nenabled = false\n'
            '[features]\ncode_mode = true\ncode_mode_host = true\n'
            'enable_request_compression = false\n'
            '[model_providers.qualification]\nname = "Local qualification fixture"\n'
            f'base_url = "http://127.0.0.1:{server.server_port}/v1"\n'
            'wire_api = "responses"\nrequires_openai_auth = false\nsupports_websockets = false\n'
            'request_max_retries = 0\nstream_max_retries = 0\n'
        )
        environment = {
            "HOME": str(home), "CODEX_HOME": str(home), "TMPDIR": str(home),
            "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "TERM": "dumb",
            "RUST_LOG": "warn,codex_code_mode=debug", "OTEL_SDK_DISABLED": "true",
        }
        command = [str(binary), "exec", "--skip-git-repo-check", "--ephemeral", "--json",
                   "Use Code Mode to apply the requested fixture patch and read it with a command."]
        process = None
        try:
            with (output / "stdout.jsonl").open("wb") as stdout, (output / "stderr.log").open("wb") as stderr:
                process = subprocess.Popen(command, cwd=project, env=environment, stdin=subprocess.DEVNULL,
                                           stdout=stdout, stderr=stderr, start_new_session=True)
                result["exit_status"] = process.wait(timeout=args.timeout)
        except (OSError, subprocess.TimeoutExpired) as error:
            result["reason"] = str(error)
        finally:
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=10)
            server.shutdown()
            server.server_close()
            thread.join(timeout=10)

        try:
            result["request_count"] = len(requests)
            result["fixture_errors"] = list(errors)
            if "reason" in result:
                raise RuntimeError(result["reason"])
            if result["exit_status"]:
                raise RuntimeError("Codex exited unsuccessfully")
            if errors or len(requests) != 2:
                raise RuntimeError("provider exchange did not complete exactly two checked requests")
            if not host.is_file() or proof.read_text() != PROOF:
                raise RuntimeError("host or delegated file result is missing")
            text = tool_output(requests[1])
            events = [json.loads(line) for line in (output / "stdout.jsonl").read_text().splitlines()]
            messages = [event.get("item", {}) for event in events if event.get("type") == "item.completed"]
            if not any(item.get("type") == "agent_message" and item.get("text") == FINAL for item in messages):
                raise RuntimeError("Codex did not finish with the checked fixture reply")
            (output / "tool-result.txt").write_text(text)
            (output / "proof.txt").write_bytes(proof.read_bytes())
            result["status"] = "pass"
        except (OSError, ValueError, RuntimeError) as error:
            result["reason"] = str(error)
        finally:
            # These requests contain only the isolated fixture environment.
            (output / "requests.json").write_text(json.dumps(requests, indent=2) + "\n")
    result["elapsed_seconds"] = round(time.monotonic() - started, 2)
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print("CODEX-INTEGRATION: " + result["status"].upper())
    if result["status"] != "pass":
        print(result.get("reason", "qualification failed"))
    return int(result["status"] != "pass")


if __name__ == "__main__":
    raise SystemExit(main())
