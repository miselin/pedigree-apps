# Codex CLI for Pedigree

This experimental package installs `codex`, including the terminal interface,
`codex exec`, and the embedded App Server. It does not require the separate
`codex-app-server` package. Use a current amd64 Pedigree kernel with
`/proc/self/exe` support and a terminal that supports ANSI control sequences.

Basic command checks pass in Pedigree. The terminal interface renders, but
startup did not reach the sign-in chooser on the tested kernel. Full CLI
qualification remains blocked by kernel stalls on one and four CPUs; this
release does not yet establish working coding sessions.

```sh
codex --help
codex login status
```

For subsequent authentication testing, `codex login --device-auth` displays a
URL and code that can be opened on another computer. This flow has not been
qualified on Pedigree.
The CLI stores credentials and session state under `$CODEX_HOME`, or
`~/.codex` by default.

The V8 Code Mode host is not included. Models whose metadata requires Code Mode,
including GPT-6 Astra and GPT-5.6 in this snapshot, cannot execute tools without
that host. GPT-5.5 supports the direct tool path in the bundled catalog; account
access and live model metadata still apply.

The package preserves upstream approval and sandbox settings. The default
Linux sandbox needs kernel facilities and bubblewrap that this package does
not supply. Once startup is working, full access can be selected explicitly
on a trusted system:

```sh
codex --model gpt-5.5 --sandbox danger-full-access --ask-for-approval never
```

Install `git` for repository operations and `ripgrep` for `rg` searches, plus the
compiler and test tools needed by your project. `ca-certificates` supplies the
system trust store. Managed daemon installation and Code Mode are not qualified.
No credentials or background services are installed by this package.

On kernel `6cb21345c`, commands that request a new PTY fail because musl
`openpty()` requires the missing `TIOCSPTLCK` ioctl. Running the CLI in an
existing terminal is a separate path. Commands using pipes still require
target qualification. A four-CPU test captured a kernel TLB-invalidation
panic; the one-CPU run stopped in general-protection exception handling.

Version `0.0.0.20260907` identifies upstream snapshot
`694b6319d3ad2399f6e435760a22d9b9357f0697`. Source, toolchain, dependency and patch
checksums are recorded in `build.json`; upstream and dependency notices are
installed alongside this document.
