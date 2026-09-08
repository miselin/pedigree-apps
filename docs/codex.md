# Codex on Pedigree

The `codex` recipe combines the terminal client, embedded App Server and Code
Mode host in one PUP. Its two executables are `/usr/libexec/codex` and
`/usr/libexec/codex-code-mode-host`. The `codex-app-server` command invokes
`codex app-server`; the separate 217 MB App Server executable is not included.

The recipe builds `codex-cli` and `codex-code-mode-host`, checks their source
revision and executable hashes, and merges their completed package roots.
Identical shared files are accepted; conflicting contents, modes or file types
fail the build. Component defaults, notices and provenance are retained.

```sh
./buildPackages.sh --only codex
./buildPackages.sh --only codex --audit-only
```

The snapshot version is `0.0.0.20260907`, based on Codex revision
`694b6319d3ad2399f6e435760a22d9b9357f0697`. The package depends on
`ca-certificates`; Bash and coreutils are target image prerequisites. Git,
ripgrep and project build tools can be installed separately.

The Code Mode host is another Rust executable, embedding V8 through matching
Rust bindings. It does not require Node.js. Its V8 15.0 engine is statically
included, so the V8 13.6 development PUP is not a runtime dependency.

Existing CLI and standalone App Server packages remain available. PUP overlays
files and does not remove obsolete files, so installing the combined package
does not reclaim an older standalone App Server binary. No migration script
deletes previously installed files.

## Runtime configuration

Upstream already enables the Code Mode host feature and discovers the host
beside the actual Codex executable. The package needs no user configuration
override for host discovery. Upstream models, approvals and sandbox defaults
are preserved.

Initial command execution on Pedigree requires an explicit full-access policy
because Linux process sandboxing is incomplete. V8's in-process memory sandbox
is a separate mechanism and remains enabled. PTY command creation still needs
the missing `TIOCSPTLCK` ioctl on the tested `6cb21345c` kernel.

## Qualification

Component evidence is in [CLI qualification](codex-cli.md) and
[Code Mode host qualification](codex-code-mode-host.md). Earlier CLI tests
passed basic commands but encountered kernel failures during full startup.
Packaging both executables does not resolve those failures or establish
authenticated coding sessions.

`scripts/qualify-codex-integration.py` exercises the actual CLI, its embedded
App Server and the discovered Code Mode host against a local scripted
Responses provider. The provider supplies a fixed JavaScript cell that uses
`apply_patch`, runs a pipe-backed `cat` command, and awaits a Promise. The
check requires exact command output, exit code zero, the computed value 42,
an independently verified file, a final response and a clean CLI exit.

The test uses a private home, no credentials, and explicit full access limited
to the test invocation. It should run in an isolated environment with external
network access disabled. It establishes local integration only; it does not
test authentication, model inference, TLS or sandbox enforcement.

```sh
python3 scripts/qualify-codex-integration.py \
  --codex /usr/libexec/codex \
  --output-dir .build/codex-code-mode/integration --timeout 120
```

Use a new output directory for every run. The result records executable
hashes, checked provider requests, tool results and process output. The
missing-host Linux control fails when Codex falls back to ordinary tools.

The Linux reference passed on 2026-09-07 with exactly two provider requests,
the expected file and command output, and exit status zero (6.44 seconds).
It ran with external networking disabled. Evidence is retained in
`.build/codex-code-mode/integration-linux/`; the missing-host control is in
`.build/codex-code-mode/integration-no-host/`. The combined PUP also passed
the full package audit. These are build and Linux results, not guest proof.

The direct Code Mode host is qualified in Pedigree on one and four CPUs.
The full CLI guest check first stopped before launching Codex: CPython's script
open failed with `EINVAL` because `FIOCLEX` was not routed for regular files.
Moving the existing descriptor-flag operation before device dispatch removed
that error. A subsequent run entered Python but exceeded the 110-second
prerequisite deadline. This result does not identify a Codex runtime failure.
The descriptor fix is committed in Pedigree as `22bd7223f`; all five descriptor
families and all nine host checks pass on one and four CPUs in 70.19 and
75.65 seconds. These runs use the same host executable as the published PUP.
Evidence is in `.build/codex-code-mode-host/cloexec-{1cpu,4cpu}/` and
`.build/codex-code-mode/kernel-cloexec-provenance/source.json`.

The descriptor regression also exposed a separate procfs traversal issue.
Following `/proc/self/exe` calls `VfsMountView::formatPath`, whose
`NamespaceMutation` guard changes the generation observed by the outer path
resolver. The resolver retries the same traversal. The original exec test
stalled; re-executing its ordinary absolute path passes without changing that
kernel code. Direct `readlink` has a different path and can still succeed.
The failed guest evidence and source analysis are retained in
`.build/codex-code-mode-host/fd-1cpu/` and
`.build/codex-code-mode/kernel/proc-exe-follow-findings.md`. Procfs traversal
is outside the Code Mode host qualification and remains a separate repair.

The instrumented guest retry completed `hashlib` and continued creating
standard-library bytecode while importing `http.server`, then reached the
110-second prerequisite deadline. A final retry disabled bytecode-cache writes
with `-B` and allowed 300 seconds for prerequisites. It stopped before the
wrapper-entry marker: the 90-second serial-idle watchdog captured the guest
in an exception/reporting path and ended the run. The cause of that distinct
failure is unresolved. Neither attempt launched the CLI.

The receipts, serial output and matching-symbol captures are in
`.build/codex-code-mode-host/integration-cloexec-1cpu/` and
`.build/codex-code-mode-host/integration-nopyc-1cpu/`. All retained native runs
are indexed in `.build/codex-code-mode-host/qualification-summary.json`.
Full CLI tool workflows, authenticated networking, interactive terminal
sessions and OS sandbox enforcement remain unqualified on Pedigree.

## Published package

The unified `codex` version `0.0.0.20260907` is published for amd64:

```sh
pup install codex
```

The [published PUP](https://pup.pedigree-project.org/codex-0.0.0.20260907-amd64.pup)
is 130,839,026 bytes, with SHA256
`10492a7d9f8e06a7c068700e45051f416770072cb4fe0606f7c12f7dbe3aff25`.
The public catalog, runtime dependency and downloaded archive were verified
against the final audited artifact. The release retains CLI executable SHA256
`47703e05c4248dc65e520c54f9e2d39975c2206d481a6723803c3403a4b6ac06`
and host executable SHA256
`e3364903a1c9e824e1104aa476949221154fbeff5b1013c644d9266aacd2a73a`.

Final build provenance is in `.build/codex-code-mode/package-receipt-final.json`;
public catalog and download verification for both new packages is in
`.build/codex-code-mode/published.json`. All 337 repository tests passed.
The kernel fixes `29d831db6` and `22bd7223f` are integrated into the local
Pedigree checkout. Rebuild its boot images before target use; existing main
checkout images were not replaced during this qualification.
