# Codex Code Mode host for Pedigree

This experimental package supplies the JavaScript execution host used by Codex
Code Mode. It installs `/usr/libexec/codex-code-mode-host` beside the Codex CLI,
which discovers and launches it when a session needs Code Mode.

The host uses V8 15.0.245.2 through the matching Rust `v8` 150.4.0 bindings.
Pointer compression and the V8 sandbox remain enabled. It embeds its engine,
ICU data and C++ runtime; Node.js and the separate V8 13.6 package are not required.
The `ca-certificates` dependency supports optional HTTPS telemetry export.

The default transport is framed JSON over standard input and output, with a
four-byte little-endian payload length. This is the Code Mode protocol, distinct
from the App Server's newline-delimited JSON-RPC protocol. The host also accepts
`--listen grpc://IP:PORT` for its optional gRPC transport.

The stdio host passed QEMU qualification on one and four CPUs: protocol and
session setup, JavaScript, Promises, delegated callbacks, exception recovery,
cell termination and clean shutdown. This requires Pedigree's absolute-futex
and raw-clock extensions. Large heaps, concurrent sessions, full sandbox
reservation coverage and the optional gRPC transport remain unqualified.

This package does not change model selection, approval settings or command
sandbox policy. No credentials or background service are installed.

Snapshot version `0.0.0.20260907` identifies Codex revision
`694b6319d3ad2399f6e435760a22d9b9357f0697`. Source, dependency and engine artifact
checksums are recorded in `build.json`; dependency notices are under `dependencies`.
