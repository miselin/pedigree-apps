# Codex for Pedigree

This package includes the Codex terminal client, embedded App Server and Code
Mode host. Install it with `pup install codex`.

```sh
codex --help
codex login status
codex-app-server --listen stdio://
```

The App Server command runs the server embedded in the CLI. The Code Mode host
is discovered automatically beside the CLI executable. Neither the separate
`codex-cli` and `codex-app-server` packages nor the V8 development package is
required.

The Code Mode host passes JavaScript, Promise, callback, recovery and shutdown
checks in QEMU on one and four CPUs. It requires Pedigree's absolute-futex and
raw-clock extensions (`29d831db6` or later).

This port remains experimental. Full CLI tool workflows, interactive terminal
sessions, authenticated network access and sandbox enforcement remain
unqualified on Pedigree. Component documentation retains the individual test
results.

Upstream approval, sandbox and configuration defaults are preserved. The package
installs no credentials or background services. Install `git`, `ripgrep` and the
build tools needed by your project separately.

Existing component packages remain available. Installing `codex` does not remove
files left by earlier packages.

Version `0.0.0.20260907` uses Codex revision
`694b6319d3ad2399f6e435760a22d9b9357f0697`. Component notices, defaults and build
records are retained under their original paths. `build.json` records the exact
component executable and provenance hashes included in this package.
