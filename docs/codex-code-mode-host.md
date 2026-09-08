# Codex Code Mode host on Pedigree

The `codex-code-mode-host` port builds the standalone Rust host from Codex
revision `694b6319d3ad2399f6e435760a22d9b9357f0697`. It runs JavaScript in V8
and delegates tool requests back to its client. In a Codex session, App Server
owns those tools and their permission checks.

## Build

```sh
./buildPackages.sh --only codex-code-mode-host
./buildPackages.sh --only codex-code-mode-host --audit-only
```

The shared Codex build helper accepts `build --component code-mode-host`.
It uses one Rust compiler job, a separate source tree and separate output,
while sharing the existing Codex dependency cache. Run Codex component builds
sequentially; parallel helper invocations require separate caches.

This snapshot requires Rust crate `v8` 150.4.0 and engine V8 15.0.245.2.
The V8 13.6.233.17 embedding PUP has a different API and cannot supply this
binding's library. The port selects the exact matching OpenAI Linux-musl
archive and generated bindings, verifies both checksums, and retains
pointer compression and the V8 sandbox. The archive includes matching LLVM
C++ runtime objects. ICU data is embedded through `deno_core_icudata`.

The host application source is unchanged. A Pedigree Cargo feature enables
the pinned vendored OpenSSL dependency, avoiding build-host TLS libraries.
It is cross-built with Rust 1.95 for the Linux-musl ABI supported by Pedigree.
Engine inputs and notices supplement
the general Cargo dependency provenance, because the published Rust crate
does not contain every engine and C++ runtime license file.

The actual host is installed at `/usr/libexec/codex-code-mode-host`, beside
the actual CLI executable. This is the upstream discovery location. The
default transport uses four-byte little-endian length-prefixed JSON on
standard input and output. App Server's newline-delimited JSON-RPC protocol
is different. The optional gRPC transport is outside the initial scope.

## Qualification

Build the protocol probe with the Pedigree SDK:

```sh
mkdir -p .build/codex-code-mode-host/artifacts
../pedigree/pedigree-compiler-15.3.0-r2/bin/x86_64-pedigree-gcc \
  -static -O2 -Wall -Wextra -Werror \
  language-ports/codex-code-mode-host/probe.c \
  -o .build/codex-code-mode-host/artifacts/codex-code-mode-qualify
python3 scripts/qualify-language-ports.py \
  --iso ../pedigree/build/pedigree.iso --disk ../pedigree/build/hdd.img \
  --suite language-ports/codex-code-mode-host/suite.json \
  --memory 4096 --cpus 1 --timeout 900 --disk-size-mib 4096 \
  --output-dir .build/codex-code-mode-host/qemu-1cpu
```

Use freshly built images and retain the kernel revision with each result.
Repeat with four CPUs and a fresh output directory after the one-CPU run.

The nine stages check protocol negotiation, session creation, arithmetic and
stored values, Promises and a checked mock callback, exceptions and recovery,
yielding and termination, recovery after termination, and clean EOF shutdown.
The fixture tests exercise the probe's rejection paths; only runs against the
actual host can establish host compatibility.

The independent [Codex integration check](codex.md) adds real delegated file
editing and pipe-backed command execution. Neither check establishes
authenticated model sessions, PTY commands, durable storage, or OS sandbox
enforcement. The earlier V8 13.6 guest qualification does not qualify this
newer engine's sandbox reservations or concurrent runtime behavior.

On 2026-09-07 the static host built successfully and passed the package audit.
Its executable SHA256 is
`e3364903a1c9e824e1104aa476949221154fbeff5b1013c644d9266aacd2a73a`.
The build peaked at 3.41 GiB without swap or OOM events. The Linux reference
passed all nine protocol stages, and all 18 probe fixture tests passed.

The first Pedigree run used the frozen `6cb21345c` kernel on one CPU with
4 GiB RAM. Handshake and session creation passed, but arithmetic aborted
with `Futex operation failed with error -38` from Abseil. The host exited
with signal 6 and the probe reaped it cleanly. This identifies an unsupported
realtime futex wait; it was not a timeout. Full logs, injected binary hashes
and image provenance are in
`.build/codex-code-mode-host/qemu-baseline-1cpu/receipt.json` and its adjacent
files. The failed baseline is retained independently of later kernel fixes.

With Pedigree's absolute-futex and raw-clock extensions, the same host executable
passed all nine stages on one and four CPUs with 4 GiB RAM. Those runs also
passed the new eight-case futex suite and the existing signal, timer, clock,
clock-adjustment and legacy futex regressions. The combined runs took 96.45
and 119.70 seconds, respectively; both ended with clean guest shutdown.

Evidence is retained under
`.build/codex-code-mode-host/qemu-fixed-{1cpu,4cpu}/`. The frozen kernel,
source changes, configuration, symbols and image hashes are recorded in
`.build/codex-code-mode/kernel-provenance/source.json`. The build starts from
`a78f54aa5` and adds `FUTEX_WAIT_BITSET/MATCH_ANY` with absolute monotonic and
realtime deadlines, plus `CLOCK_MONOTONIC_RAW` reads through the syscall and
vDSO. Selective futex bitsets remain unsupported. No host application or V8
engine change was needed to pass these guest checks.

The kernel extensions are committed in Pedigree as `29d831db6`
(`posix: support absolute futex waits and raw clock reads`). Rebuild the kernel
and boot images from that commit or a descendant before using this host.

## Published package

`codex-code-mode-host` version `0.0.0.20260907` is published for amd64:

```sh
pup install codex-code-mode-host
```

The [published PUP](https://pup.pedigree-project.org/codex-code-mode-host-0.0.0.20260907-amd64.pup)
is 26,397,955 bytes, with SHA256
`43f7be24aef9a2f3786987369e6e05074884a346f559ead0f36a5bba7ef46533`.
The public catalog, `ca-certificates` dependency and downloaded archive were
verified against the qualified local artifact. Publication evidence is in
`.build/codex-code-mode/published-codex-code-mode-host.json`.
