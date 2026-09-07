# Codex App Server on Pedigree

This port cross-builds the standalone Codex App Server for amd64 using
Pedigree's Linux syscall compatibility and the Rust Linux-musl target.
The pinned source is OpenAI Codex revision
[`694b6319d3ad`](https://github.com/openai/codex/tree/694b6319d3ad2399f6e435760a22d9b9357f0697/codex-rs/app-server).
The PUP snapshot version is `0.0.0.20260907`; upstream's workspace version is
`0.0.0` at this revision. The audited PUP passes the stdio RPC suite on a
one-CPU QEMU guest; SMP operation remains experimental.

## Build

Use the existing Linux amd64 Docker builder:

```sh
./buildPackages.sh --only codex-app-server
./buildPackages.sh --only codex-app-server --audit-only
```

The archive is written to
`pup/package_repo/codex-app-server-0.0.0.20260907-amd64.pup`.

The recipe verifies the source archive, provisions checksum-pinned Rust 1.95
host tools and musl standard library, and vendors the complete locked Cargo
workspace. Compilation then runs with `--offline --locked`. The existing Rust
1.85.1 native compiler package remains independent of this host build tool.

For a direct build without creating a PUP:

```sh
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" \
  pedigree-apps-builder:local python3 scripts/build-codex-app-server.py build
```

Outputs are under `.build/codex-app-server/artifacts/root`. Add `--offline`
after the source, compiler components, and Cargo dependencies are cached.
`--jobs` controls compilation parallelism. Native C/C++ dependencies use the
Pedigree SDK plus an isolated, checksum-pinned Linux 6.6 UAPI header set.
Target C/C++ code selects the same Linux ABI as Rust; host libc headers and
libraries are excluded. Rust links a static executable at Pedigree's required
load address. Release debug information and LTO are disabled for the initial build.

Only the SDK's `libgcc.a` and `libstdc++.a` are exposed to Rust's linker, in an
isolated directory. Adding the SDK's full library directory selects its older
native libc before Rust's bundled musl and breaks newer syscall calls. The
package records runtime archive hashes and includes the GCC and Rust runtime notices.

## Run

Install the published package:

```sh
pup sync
pup install codex-app-server
```

The package installs `/usr/bin/codex-app-server`, which launches the executable
at `/usr/libexec/codex-app-server` with an absolute path:

```sh
codex-app-server --listen stdio://
```

A client speaks the [App Server JSONL protocol](https://learn.chatgpt.com/docs/app-server):
`initialize`, then `initialized`, followed by requests. This package contains
the server, not the Codex terminal UI. It requires `ca-certificates`; install
Git and ripgrep for workflows that invoke those tools.

The Pedigree patch selects the musl allocator, supplies an absolute executable
path when `/proc/self/exe` is unavailable, and installs the upstream defaults
at `/usr/share/codex-app-server/defaults.toml`. User configuration and managed
policy retain their upstream behavior. Unsupported sandbox operations retain
their upstream failure behavior.

The separate V8-based Code Mode host is not included. Its absence limits models
and workflows that require Code Mode. Authentication, inference, tool execution,
TLS, and sandbox enforcement require their own runtime qualification; a
successful build or protocol handshake does not establish them.

The default Linux sandbox also needs bubblewrap and namespace support beyond
Pedigree's current UTS-only `unshare`. Bubblewrap is not included in this PUP.
Sandbox helpers also use `/proc/self/exe`, which kernel commit `37ca72cd7`
provides. The port retains upstream sandbox policy.

On kernel `6cb21345c`, PTY-backed command execution also needs `TIOCSPTLCK`,
which is not implemented. Codex's PTY creation paths reach musl `openpty()`
and fail on that ioctl, without automatically falling back to pipes. Explicit
`tty=false` commands use a separate pipe path that remains unqualified.

## Qualification

Build the guest protocol probe with the Pedigree SDK:

```sh
mkdir -p .build/codex-app-server/artifacts
../pedigree/pedigree-compiler-15.3.0-r2/bin/x86_64-pedigree-gcc \
  -static -O2 -Wall -Wextra -Werror language-ports/codex-app-server/probe.c \
  -o .build/codex-app-server/artifacts/codex-app-server-qualify
python3 scripts/qualify-language-ports.py \
  --iso ../pedigree/build/pedigree.iso --disk ../pedigree/build/hdd.img \
  --suite language-ports/codex-app-server/suite.json \
  --memory 4096 --cpus 1 --timeout 780 --disk-size-mib 4096 \
  --output-dir .build/codex-app-server/qemu-check-1cpu
```

The suite injects the PUP's staged root plus the current Bash, readline,
ncurses, and CA certificate roots. Build those packages first if missing.
Repeat with four CPUs and a fresh output directory. Use freshly rebuilt kernel
images containing cache-memory fix `0139dd022`, RamFs inode fix `0c8b943d6`,
cache scan fix `eff966492`, and VM fixes `fff825465` and `3da8ef40a`.
These also include `/proc/self/exe` support.

The probe starts a private server without credentials and checks initialization,
unauthenticated account state, configuration, an empty thread list, and exact
file readback. It checks response structure and values, process shutdown, and
cleanup, allowing sixty seconds for graceful shutdown. It sends no inference or
authentication request. Logs and image/payload
hashes are retained per run. Snapshot guests with `PEDIGREE_CRIPPLE_HDD` establish
behavior within a boot, not persistent disk writeback.

The suite allows ten minutes for cold startup and the RPC checks. The server
opens five SQLite databases and applies 61 migrations before accepting RPCs;
the probe reports database file sizes periodically while waiting. Set
`CODEX_APP_SERVER_QUALIFY_TIMEOUT_MS` to override its standalone four-minute
default, up to thirty minutes.

## State runtime diagnostic

After building App Server, compile the smaller SQLite state probe from the
cached release libraries:

```sh
docker run --rm --platform linux/amd64 --network none -v "$PWD:/workspace" \
  pedigree-apps-builder:local python3 scripts/build-codex-app-server.py state-probe
python3 scripts/qualify-language-ports.py \
  --iso ../pedigree/build/pedigree.iso --disk ../pedigree/build/hdd.img \
  --suite language-ports/codex-app-server/state-suite.json \
  --memory 4096 --cpus 4 --timeout 780 --disk-size-mib 4096 \
  --output-dir .build/codex-app-server/qemu-state-4cpu
```

The compile action uses the existing pinned compiler without Cargo or downloads
and writes `.build/codex-app-server/artifacts/codex-state-qualify`. It requires
one matching build generation of the `codex_state` and `tokio` release libraries;
ambiguous or incomplete caches produce an error. It does not change the PUP.

The probe checks file identity across reopen, rename, and unlink/replacement in
a private `/tmp` directory before initializing the five SQLite state databases.
Failures print the complete initialization error chain. The suite requires both
the identity preflight and state initialization to pass; it needs the current
Bash, readline, and ncurses package roots but no credentials or network access.

## RamFs database identity repair

App Server initially failed while opening its second SQLite database with
`database is locked`. RamFs reported inode zero for every node. SQLite keys
process-local lock and WAL shared-memory bookkeeping by `(st_dev, st_ino)`, so
separate databases on the same RamFs instance aliased one another.

Kernel commit `0c8b943d6` assigns stable, nonzero inode identities to RamFs files,
directories, symlinks, and the root. Allocation is atomic and never reuses IDs,
including after unlink while a descriptor remains open. The old kernel failed
the Rust identity preflight; the repaired kernel passed it and initialized all
five App Server state databases in a four-CPU QEMU guest (133.67 seconds including
boot). This is a within-boot filesystem identity repair; persistent storage
qualification remains separate.

The kernel's `ramfs-inode-contract-test` additionally checks metadata agreement,
rename/reopen stability, retained unlinked content, and 128 concurrent file
creations across four directories. It passed in both the one- and four-CPU
App Server qualification guests.

## Cache scan repair

With distinct inodes fixed, the full server still exceeded a ten-minute startup
probe on one CPU and failed state initialization on four CPUs. Limiting Tokio
to two workers did not resolve the four-CPU failure.

The cache timer restarted its scan after queueing each dirty page but only
recorded visited dirty pages. It repeatedly checksummed the same clean prefix
within one epoch. Disabled disk writes in snapshot qualification left dirty
pages retrying, making this especially expensive with a large executable cached.

Kernel commit `eff966492` records every visited page for the epoch. It retains
dirty flags, failed-write retries, explicit sync behavior, and page ownership.
The new `CacheSync.TimerChecksCleanPrefixesOncePerEpochAndServicesLaterChanges`
regression fails against the old timer and passes after the fix. All 32 selected
cache, paging, and filesystem sync tests passed. The host build temporarily
allowed existing missing-override, sign-comparison, and floating-point-comparison
warnings; its original flags were restored afterward.

The test images retain their existing Debug build, logging, lock tracking, and
`PEDIGREE_CRIPPLE_HDD=TRUE` settings. The cache repair does not enable disk writes
or change the App Server executable or worker settings.

## Initial verification record

On 2026-09-07, the complete one-CPU QEMU suite passed all five RPC checks,
graceful EOF shutdown, and private-directory cleanup in 487.21 seconds including
boot. The guest used 4 GiB RAM, `-cpu max`, the default Tokio worker count, and
kernel source through `eff966492`. Networking was disabled and no credentials
were supplied. The ISO SHA-256 was
`c345cd8d2475c6986608720056c28e9bef461bc783f4deb60fca5406bf63fb0b`.

The static App Server executable is 216,900,832 bytes, with SHA-256
`35734f6e09ad466cd33ee6422b0adaab140517a5063b3de357f8251bc3001130`.
The PUP artifact audit passes, including exact agreement with its staged root.
All 289 package tests passed. The Linux reference run, with networking disabled,
passed all five RPC checks and graceful shutdown.

On the repaired kernel, the first one-CPU run passed all five RPC checks but
needed termination after the original ten-second shutdown allowance. Repeating
with sixty seconds allowed graceful shutdown and produced the passing result
above. The four-CPU run passed initialization and account read, then terminated
with SIGSEGV during `config/read`. This run predates the VM repairs described
below. Authentication, inference, TLS, sandboxed tools, and persistent storage
remain outside the qualification scope.

Logs, injected payload hashes, and image hashes are retained under
`.build/codex-app-server/`. Relevant runs are `linux-reference-final.log`,
`qemu-identity-baseline-4cpu`, `qemu-state-fixed-4cpu`,
`qemu-cache-fixed-1cpu`, `qemu-cache-fixed-4cpu`, and the final passing
`qemu-stdio-1cpu`. Failed and interrupted runs are retained alongside subsequent
attempts.

The final archive includes updated package notes after the guest image was
prepared; the executable and runtime defaults are unchanged. The final archive
and staged root passed the artifact audit again.

Initial PUP SHA-256:
`b519b67878b238dc49300f6e5b82d91411f6ca5d37d6566c49da49108c2aad64`.

## VM repairs and release qualification

Kernel `fff825465` repairs large sparse mapping replacement and cleanup.
Kernel `3da8ef40a` repairs deferred page-fault handling: a concurrently
published mapping resolves the fault only if it permits the original access.
A write fault can replace a concurrently published read-only zero page.

Release images were freshly rebuilt from clean kernel `6cb21345c`, which
contains those repairs. Image and source provenance is retained under
`.build/codex-publication/kernel-provenance/`. The ISO SHA-256 is
`ff36e9f334ef026d637f0455c2da638b7c62c9902cb4c4a9e4a0661c2b7103dd`.

The complete one-CPU suite passed all five RPC checks, graceful EOF shutdown,
and private-directory cleanup in 483.71 seconds including boot. The executable
is unchanged from the initial qualification. Evidence is retained under
`.build/codex-publication/app-server-1cpu/`. The guest used 4 GiB RAM,
`-cpu max`, no network interface or credentials, and snapshot disks with
`PEDIGREE_CRIPPLE_HDD=TRUE`.

The four-CPU release run stalled during initialization. Its last probe
heartbeat was around 333 seconds after launch; serial output stopped around
336 seconds, and the runner reached its 900.12-second outer timeout. No panic
or SIGSEGV was reported. Evidence is retained under
`.build/codex-publication/app-server-4cpu/`, including a stall observation.
SMP operation remains unqualified despite repair of the original page-fault
bug. Authentication, inference, agent tool execution, and durable storage also
remain outside the release qualification.

A bounded four-CPU diagnostic retry also stopped making progress. After
77 seconds without serial output, QEMU was paused for register reads and
frame-pointer walks, then terminated. CPU 0 was waiting in `SlamCache::free`
during `mkdir` path cleanup; CPU 1 was waiting in `SlamCache::allocate` while
the deferred time-accounting worker allocated its process snapshot. Both
waited on recovery lock `0xffff9000c40068a0`. This captures allocator lock
contention; it does not identify the owner or prove a particular deadlock.

CPU 2's captured stack ended at an interrupt boundary in time accounting.
Reading the lock's ownership fields and that CPU's saved interrupt context
would distinguish a faulted holder from corrupted or abandoned ownership.
The bounded capture, raw registers, symbol hashes, and serial log are retained
under `.build/codex-publication/app-server-diagnostic-4cpu/`. No kernel source
was changed during this release qualification.

## Publication

The amd64 PUP was published on 2026-09-07. Its public catalog entry records
`ca-certificates` as its runtime dependency. A fresh download from
`https://pup.pedigree-project.org` matched the audited local archive:

- Size: 82,246,474 bytes.
- SHA-256: `487bda8e48259cce2bfe2d57685bf548c27fbd8e193d38ad56b8399ee972f8fc`.

The release archive updates the package documentation after guest qualification;
all other staged files, including the executable and runtime defaults, are
unchanged. The repacked root and archive passed the complete artifact audit.
Publication and public-download evidence is retained under
`.build/codex-publication/` in `publish-app-server.log`,
`public-verification-app-server.log`, and `published-codex-app-server.json`.
