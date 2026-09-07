# Codex App Server for Pedigree

This experimental package provides Codex's JSON-RPC server for client
applications on amd64 Pedigree. It uses the Linux musl ABI and a Pedigree
compatibility patch. Authenticated agent sessions and tool execution remain
experimental; the default Linux sandbox needs additional kernel support and
bubblewrap, which this package does not supply.

Use a kernel containing RamFs inode fix `0c8b943d6`, cache scan fix
`eff966492`, and VM fixes `fff825465` and `3da8ef40a`. The release test images
were rebuilt from kernel `6cb21345c`. The one-CPU QEMU suite passes
initialization, account read, configuration read, thread listing, file readback,
and graceful shutdown. A four-CPU release run stalled during initialization
without reporting SIGSEGV; SMP operation remains unqualified.

Start the server over stdio:

```sh
/usr/bin/codex-app-server --listen stdio://
```

A client exchanges newline-delimited JSON over stdin and stdout, beginning
with the App Server initialization handshake. This package contains the server;
the `codex-cli` package supplies the terminal UI. Neither package includes the
separate V8 Code Mode host.

The `ca-certificates` dependency supplies the system trust store. The target
image already supplies Bash and coreutils. Install `git` for repository
operations and `ripgrep` for workflows that invoke `rg`; neither is required
for the stdio protocol itself.

Build or package success does not establish sandbox enforcement, authenticated
network access, or child-process execution on Pedigree. Those capabilities
require separate target qualification. This package installs no credentials
and enables no background service.

Package version `0.0.0.20260907` identifies an upstream snapshot whose workspace
version is `0.0.0`: revision
`694b6319d3ad2399f6e435760a22d9b9357f0697`. Source and dependency checksums are
recorded in `build.json`.

The upstream Apache-2.0 license and attribution notice are installed here as
`LICENSE` and `NOTICE`.
