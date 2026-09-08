# Codex CLI on Pedigree

The `codex-cli` package provides `/usr/bin/codex`, including the terminal
interface, noninteractive commands, and the embedded App Server. It uses the
same pinned Codex revision and Rust Linux-musl target as the standalone
[`codex-app-server` package](codex-app-server.md). These component packages
omit the separately packaged [Code Mode host](codex-code-mode-host.md).
The combined [`codex` PUP](codex.md) includes the CLI and that host and has
passed the package audit.

This is an experimental port. Basic commands pass in Pedigree, while earlier
terminal-startup and embedded-RPC runs failed in the kernel. The Code Mode host
now passes its direct checks on one and four CPUs; full CLI integration on
Pedigree remains unqualified because the [integration fixture](codex.md) stopped
before launching the CLI. Working authenticated coding sessions are not yet
established.

## Build and install

```sh
./buildPackages.sh --only codex-cli
./buildPackages.sh --only codex-cli --audit-only
```

The snapshot version is `0.0.0.20260907`, based on upstream revision
`694b6319d3ad2399f6e435760a22d9b9357f0697`. Upstream reports version `0.0.0`
at this revision. The archive is
`pup/package_repo/codex-cli-0.0.0.20260907-amd64.pup`.

The executable is statically linked and cross-built with the pinned Rust 1.95
host toolchain. A native Rust compiler is not required to run it. The package
uses the musl allocator and includes upstream and dependency license notices.
The Pedigree feature selects `crossterm/libc` for standard termios calls.
The default terminal path uses `TCGETS2`, which kernel `6cb21345c` rejects with
`EINVAL`; a small guest diagnostic verifies that libc raw mode, PTY byte
transfer, and settings restoration work on the same kernel.
The recipe compiles one Rust job at a time to limit host memory usage.
The direct build helper shares its cache with App Server; run helper invocations
sequentially, or provide separate `--cache` directories.
An 8 GiB Docker VM ran out of memory when compiling this port alongside V8,
including with one CLI compiler job. Run those large builds sequentially on
that configuration. The release compilation ran with a 6 GiB memory cap and
1 GiB swap allowance. It reached the memory cap and reclaimed memory without
an OOM or observed swap use.

Install through PUP:

```sh
pup sync
pup install codex-cli
```

PUP installs `ca-certificates` as a dependency. The target image must already
provide Bash and coreutils. Install `git`, `ripgrep`, and the build tools needed
by the projects you intend to work on. The standalone `codex-app-server` PUP
is not required by the CLI.

## Runtime scope

The package retains upstream permission and model configuration. Pedigree's
Linux sandbox support is incomplete, so initial agent sessions require an
explicit full-access configuration. Full access does not supply Code Mode.

The bundled model catalog requires Code Mode for GPT-6 Astra and GPT-5.6
Sol/Terra/Luna. GPT-5.5 supports the ordinary tool path in this snapshot;
actual model availability and requirements come from the account's live
catalog. The matching V8 15.0 Code Mode host now passes all nine direct
protocol/runtime checks on one and four CPUs with Pedigree's absolute-futex
and RAW-clock extensions. It is included in the combined `codex` PUP and
can also be built as the `codex-code-mode-host` component. Its V8 sandbox
remains enabled. The [combined integration check](codex.md) passes against a local
scripted provider on Linux; the native CLI workflow remains unqualified after
the documented prerequisite failures. Direct host
qualification alone does not qualify a CLI agent turn.

Authentication, model requests, agent-driven editing, sandbox enforcement,
and persistent session recovery require their own runtime qualification.
Package audit and command startup do not establish those capabilities.

Kernel `6cb21345c` does not implement `TIOCSPTLCK`, which musl `openpty()`
requires. Codex-created PTY commands therefore have a known compatibility gap,
even when the CLI itself runs in an existing terminal. There is no automatic
pipe fallback after PTY creation fails; explicit `tty=false` commands use a
separate, still-unqualified path.

## Qualification

The guest suite checks version/help output, logged-out status, the embedded
App Server's five RPC checks and graceful shutdown, and the sign-in chooser
in a private PTY. It answers terminal queries, requests a resize, and exits
with Ctrl-C without selecting an authentication option. Each child receives
an isolated home and an explicit environment without credentials. The test
disables welcome animation in its private configuration and recognizes both
upstream API-key labels despite cursor-positioned whitespace.

Build both protocol probes with the Pedigree SDK:

```sh
mkdir -p .build/codex-cli/artifacts .build/codex-app-server/artifacts
../pedigree/pedigree-compiler-15.3.0-r2/bin/x86_64-pedigree-gcc \
  -static -O2 -Wall -Wextra -Werror language-ports/codex-cli/probe.c \
  -o .build/codex-cli/artifacts/codex-cli-qualify
../pedigree/pedigree-compiler-15.3.0-r2/bin/x86_64-pedigree-gcc \
  -static -O2 -Wall -Wextra -Werror language-ports/codex-app-server/probe.c \
  -o .build/codex-app-server/artifacts/codex-app-server-qualify
python3 scripts/qualify-language-ports.py \
  --iso ../pedigree/build/pedigree.iso --disk ../pedigree/build/hdd.img \
  --suite language-ports/codex-cli/suite.json \
  --memory 4096 --cpus 1 --timeout 3000 --disk-size-mib 4096 \
  --output-dir .build/codex-cli/qemu-check-1cpu
```

Use freshly rebuilt images containing kernel fixes `fff825465` and
`3da8ef40a`, plus the earlier fixes required by App Server. Repeat with four CPUs
and a fresh output directory. The suite also injects the current Bash,
readline, ncurses, and CA certificate package roots. These checks use serial
output and a private PTY; they do not qualify VGA rendering or physical
keyboard input. Snapshot guests do not establish durable disk writeback.

## Release evidence (2026-09-07)

The amd64 package is published at
[`codex-cli-0.0.0.20260907-amd64.pup`](https://pup.pedigree-project.org/codex-cli-0.0.0.20260907-amd64.pup).
Its public catalog metadata, CA certificate dependency, and downloaded archive
were verified against the local audited artifact. The archive is 104,441,846
bytes with SHA256
`a63fbd71ed7e16268577bc5c9e256fc2acdc9230fb10556c8249bd3f40ba8220`.
The final repack changed only the two installed qualification documents;
the tested executable and all other payload files remained identical.

The static executable at `/usr/libexec/codex` is 277,944,192 bytes with SHA256
`47703e05c4248dc65e520c54f9e2d39975c2206d481a6723803c3403a4b6ac06`.
The CLI patch SHA256 is
`16c05330af4cfff07715114b760bbccdde70e8a77371875a3837e56aa90aa2d8`;
the shared App Server patch remains
`8720e3bb66b187783ff61ae2596ddee9390aab5f72f3814aca1fc82370d339d7`.
All ten patched source files match the pinned upstream archive plus these
patches applied without fuzz.

The revised package passes the full artifact audit. Its exact executable and
launcher pass all five suite cases in an offline Linux reference container
in 12.38 seconds, including private-PTY onboarding and clean shutdown. The
same probe source builds with the host compiler for this reference and the
Pedigree SDK for the guest tests.

The final executable passes version, help, and logged-out status on both one
and four CPUs with kernel `6cb21345c075b9a66eb55863b874afcbd8b0abfc`.
Both full suites stop during the embedded server's `initialize`, before the
PTY case. A watchdog captures registers and bounded stack frames after
90 seconds without any serial output, then stops the owned guest:

| Guest | Elapsed | Captured failure |
| --- | --- | --- |
| One CPU | 332.97 s | Vector 13 general-protection handler with exception-reporting `StaticString` frames; the underlying cause is unresolved. |
| Four CPUs | 509.91 s | Mapping-invalidation panic and terminal halt on multiple CPUs; the failed phase and responsible peer are unresolved. |

A separate one-CPU PTY run renders the actual Codex interface, with model and
directory initially showing `loading`, but times out after a 600-second
guest allowance (654.10 seconds overall). It does not reach the chooser or
establish keyboard interaction, resizing, or a normal exit. The libc termios
change removes the previous immediate `EINVAL`; it does not resolve startup.

The full suites allowed 1,200 seconds per RPC and PTY case and 3,000 seconds
overall; the serial-idle watchdog ended them earlier. Every guest had 4 GiB
RAM and a private disk snapshot. Exact images and matching kernel/module
symbols are retained under `.build/codex-publication/kernel-provenance/`.
Kernel commit `a78f54aa5`, added elsewhere during testing, introduces AHCI;
it was not in these images. No kernel changes were made for this CLI port.

These are failed full-suite results. The earlier executable's successful RPC
checks below do not qualify the final executable. Authentication, model
traffic, command execution, and durable state remain untested on Pedigree.

### Earlier candidate and kernel diagnostics

The initial candidate passed the full artifact audit and all five suite cases
in an offline Linux reference container, including private-PTY onboarding and
clean shutdown. Its executable SHA256 was
`1d941e04c405da962f714ed78bc5156a0fa6fb831d75cf750b875ef5c00f2dfe`.
The first terminal
reference run exposed an incorrect test expectation for cursor-positioned
spaces and the default API-key label; the corrected probe passes without
changing the CLI executable.

The initial one-CPU Pedigree run passed version, help, logged-out status, and
all five embedded App Server RPCs with clean EOF shutdown. It ended after
703.16 seconds when the PTY probe failed before launching Codex: the SDK's
musl `unlockpt()` invokes `TIOCSPTLCK`, which Pedigree does not implement. The
probe now follows the kernel's tested `/dev/ptmx` and `TIOCGPTN` interface,
opening the slave without that unlock request.

The same initial executable passed version, help, logged-out status,
`initialize`, `account/read`, and `config/read` on four CPUs. It reached the
600-second RPC deadline during `thread/list`, then stopped producing serial
output. The watchdog captured the guest and ended the run after 823.25 seconds.
CPU0 was in `X64MappingMutationScope::panicInvalidationFailure()` while an ATA
worker mapped a new cache page. CPUs1 and 2 had entered panic shutdown;
CPU3 remained in exception handling. This is a kernel TLB-invalidation failure,
not simply a userspace timeout. The failed invalidation phase and responsible
peer are not established by the capture.

For a follow-up kernel capture, inspect the retained Local APIC terminal-failure
state, last TLB generation and per-CPU service tokens at the first invalidation
failure, together with CPU3's saved interrupt state. The panic waits for its
peers before printing, which explains the absence of a literal serial panic
message in this run.

Build, audit, and reference records are retained locally:

- `.build/codex-cli-retry-exec-recursion.log`
- `.build/codex-cli-build-libc.log`
- `.build/codex-cli-patch-verification.log`
- `.build/codex-cli-package-finalize.log`
- `.build/codex-cli-package-receipt.json`
- `.build/codex-cli-package-finalize-libc.log`
- `.build/codex-cli-package-receipt-libc.json`
- `.build/codex-publication/cli-linux-reference-v2-result.json`
- `.build/codex-publication/cli-linux-reference-v2.log`
- `.build/codex-publication/cli-libc-linux-reference-result.json`
- `.build/codex-publication/cli-libc-linux-reference.log`
- `.build/codex-publication/cli-libc-linux-reference-diagnostics-result.json`
- `.build/codex-publication/cli-libc-qualification-summary.json`
- `.build/codex-publication/cli-libc-pty-1cpu/result.json`
- `.build/codex-publication/cli-libc-pty-1cpu/serial.log`
- `.build/codex-publication/cli-libc-1cpu/result.json`
- `.build/codex-publication/cli-libc-1cpu/receipt.json`
- `.build/codex-publication/cli-libc-1cpu/gdb-registers-backtraces.json`
- `.build/codex-publication/cli-libc-4cpu/result.json`
- `.build/codex-publication/cli-libc-4cpu/receipt.json`
- `.build/codex-publication/cli-libc-4cpu/gdb-registers-backtraces.json`
- `.build/codex-publication/cli-1cpu/result.json`
- `.build/codex-publication/cli-1cpu/metadata.json`
- `.build/codex-publication/cli-1cpu/serial.log`
- `.build/codex-publication/cli-4cpu/result.json`
- `.build/codex-publication/cli-4cpu/gdb-registers-backtraces.json`
- `.build/codex-publication/terminal-probe/qemu-1cpu/result.json`
- `.build/codex-publication/terminal-probe/qemu-1cpu/serial.log`
- `.build/codex-publication/tests-release-final.log` (298 tests passed)
- `.build/codex-publication/codex-cli-repack.json`
- `.build/codex-publication/published-codex-cli.json`
