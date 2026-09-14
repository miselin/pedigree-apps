# Port status

The current catalog contains 83 active Pedigree ports and 15 explicit disabled
or deferred entries. An active entry is loadable by the package builder; it
does not by itself claim a completed integrated build or successful execution
on Pedigree.

## Local workflow

The maintained path is the local amd64 Docker builder described in
[`README.md`](README.md). It uses the current Pedigree cross-toolchain, stages
each package under `newpacks/x86_64/<package>/<version>/root`, and enforces the
target FHS layout, primarily under `/usr`, `/etc`, and `/var`. Builds are local
by default and do not upload unless an upload option is explicitly selected.

Recipes keep the upstream source version separate from the immutable PUP release
version. A Pedigree-specific payload revision is numeric and appended as an
extra component, such as `5.3.15.1`; this remains newer under PUP ordering and
also gives changed archives a new CDN cache identity. Existing completed roots
can be republished without recompilation with `--repackage-only`.

List the active catalog or inspect a dependency closure without building:

```sh
./buildPackages.sh --list
./buildPackages.sh --dry-run --only-depends python3
```

## Active catalog

| Port | Version | Port | Version | Port | Version |
| --- | --- | --- | --- | --- | --- |
| apache2 | 2.4.68 | apr | 1.7.6 | apr-util | 1.6.5 |
| atk | 2.38.0 | autoconf | 2.73 | bash | 5.3.15.1 |
| bind | 9.11.37 | binutils | 2.46.1 | bsdtar | 3.8.9 |
| ca-certificates | 2026.08.13 | cairo | 1.18.4 | cmake | 4.4.3 |
| coreutils | 9.11 | curl | 8.22.0 | dialog | 1.3.20260721 |
| diffutils | 3.12 | dropbear | 2026.94.3 | e2fsprogs | 1.47.4 |
| expat | 2.8.4 | fontconfig | 2.18.3 | fribidi | 1.0.16 |
| gawk | 5.4.1 | gcc | 15.3.0 | gdbm | 1.26 |
| gettext | 1.0 | git | 2.55.0 | glib | 2.88.3 |
| gnumake | 4.4.1 | grep | 3.12 | gzip | 1.14 |
| harfbuzz | 14.4.0 | inetutils | 2.8 | less | 704 |
| libffi | 3.8.0 | libfreetype | 2.14.3 | libgmp | 6.3.0 |
| libiconv | 1.19 | libmpc | 1.4.1 | libmpfr | 4.2.2 |
| libpcre | 8.45 | libpcre2 | 10.48 | libpipeline | 1.5.8 |
| libpng | 1.6.58 | libtool | 2.6.2 | lua | 5.5.1 |
| lynx | 2.9.3 | m4 | 1.4.21 | man-db | 2.13.1 |
| mandoc | 1.14.6 | mesa | 25.0.7 | mtools | 4.0.49 |
| nano | 9.2 | nasm | 3.02 | ncurses | 6.6 |
| openssh-client | 10.5.1 | | | | |
| openssh-sftp-server | 10.5.1 | | | | |
| openssl | 3.5.8 | pango | 1.58.2 | perl | 5.44.0.1 |
| pixman | 0.46.4 | pup | 1.2 | python3 | 3.14.7 |
| readline | 8.3.3 | sdl2 | 2.32.10 | sed | 4.10 |
| slang | 2.3.3 | sqlite | 3.53.4 | vim | 9.2.1031 |
| vttest | 20251205 | wget | 1.25.0 | zlib | 1.3.2 |
| go | 1.26.5 | ripgrep | 15.2.0 | rust | 1.85.1 |
| patch | 2.8 | | | |
| abseil-cpp | 20250512.1 | protobuf | 35.0 | | |
| git-lfs | 3.8.0 | | | | |
| codex-app-server | 0.0.0.20260907 | codex-cli | 0.0.0.20260907 | codex | 0.0.0.20260907 |
| v8 | 13.6.233.17 | codex-code-mode-host | 0.0.0.20260907 | | |

The Go target and Rust cross toolchain have runtime qualification in QEMU on
one and four CPUs. Rust currently uses the Linux-musl ABI; ripgrep is built
from source with its locked Cargo dependencies and the musl allocator. Native
compiler qualification is tracked separately in
[`docs/language-ports.md`](docs/language-ports.md).
All three PUP packages pass the artifact audit. The native Go and Rust compiler
packages remain experimental until guest application builds complete.

V8 supplies C++ embedding headers, a static library, pkg-config metadata, and
the `v8-qualify` example. Its interpreter and baseline JIT profiles pass on
one and four CPUs, including the default 512 MiB code reservation. The PUP
passes the artifact audit. Build commands, the focused Abseil suite, and
qualification limits are in [`docs/v8.md`](docs/v8.md). Node.js and npm remain
separate follow-ups.

Codex App Server and Codex CLI snapshot 0.0.0.20260907 are published.
App Server passes all five stdio RPC checks plus
graceful shutdown in one-CPU QEMU on the repaired kernel. A four-CPU release
run stalls during initialization with allocator lock contention; SMP remains
unqualified. The matching Codex CLI port passes basic command checks and
renders its terminal UI, but earlier startup and embedded RPC runs failed
in the kernel. Build instructions and qualification records are in
[`docs/codex-app-server.md`](docs/codex-app-server.md) and
[`docs/codex-cli.md`](docs/codex-cli.md). Authenticated agent sessions remain
unqualified.

The published unified `codex` PUP includes the CLI and the matching Code Mode host,
with an App Server command that uses the CLI's embedded server, and passes
the package audit. The host passes all nine direct protocol/runtime checks
in QEMU on one and four CPUs with the absolute-futex and RAW-clock kernel
extensions. Full CLI integration on Pedigree remains unqualified; the local
scripted-provider integration passes on Linux. The host embeds V8 15.0.245.2
through Rust bindings 150.4.0; it has no Node.js or V8 13.6 runtime dependency.
Build and qualification details are in
[`docs/codex.md`](docs/codex.md) and
[`docs/codex-code-mode-host.md`](docs/codex-code-mode-host.md).

Git LFS 3.8.0 is built from the upstream vendored source release with the
Pedigree Go toolchain. Its runtime closure includes Git, the system trust
bundle, and the Dropbear SSH client. The PUP passes the artifact audit; target
repository transfers remain unqualified.

Python 3.14.7 replaces the disabled Python 2 recipe and also provides
`/usr/bin/python` as a compatibility link.

The `abseil-cpp` 20250512.1 and protobuf 35.0 ports provide the shared C++
runtime libraries, headers, CMake/pkg-config metadata, and target-native
`protoc` compiler needed to build and run protobuf-based Pedigree software.
Protobuf declares Abseil as its runtime dependency.

PUP 1.2 installs its Python 3 client at `/usr/bin/pup`, its configuration at
`/etc/pup/pup.conf`, and its local package database and cache under
`/var/lib/pup`. The target client uses the Python standard library for HTTPS;
its runtime closure explicitly includes Python 3 and the system trust bundle.
Dependency-aware catalogs are resolved transitively in dependency-first order,
while historical catalogs without that optional metadata remain readable.

Mandoc 1.14.6 supplies the manual-page formatter, while man-db 2.13.1 owns
`/usr/bin/man` and the manual-page database. The recipes avoid a file conflict
by installing mandoc's user-facing aliases with `mandoc-` prefixes. S-Lang
2.3.3 uses the catalog's ncurses terminfo database and omits interfaces backed
only by unimplemented Pedigree libc stubs.

The `ca-certificates` port installs the versioned Mozilla-derived trust bundle
at `/etc/ssl/cert.pem` for the catalog's HTTPS clients.

OpenSSH 10.5p1 is split at the client/server boundary. `openssh-client`
provides `ssh`, modern `scp`, `sftp`, key tools, and the client-side agent,
while `openssh-sftp-server` supplies Dropbear's external SFTP subsystem.
Dropbear remains the packaged SSH daemon. PKCS#11, FIDO, setuid host-based
authentication, and the OpenSSH daemon are deferred pending their own runtime
and privilege-boundary qualification.

Bootable images must install Bash and coreutils as the target script baseline
before ordinary ports. This supplies `/usr/bin/bash`, `/usr/bin/env`, and the
basic utilities used by installed shell scripts; the image's FHS aliases expose
Bash as `/usr/bin/sh` and `/bin/sh`. Treating this as the base contract avoids a
Bash, Readline, and ncurses dependency cycle. Perl, Python 3, and any other
non-baseline interpreters remain explicit recipe runtime dependencies and are
checked against staged executable scripts.
Documentation examples are not treated as installed commands.

## Compatibility ceilings

- BIND is held at 9.11.37, the final release compatible with the catalog's
  current dependencies. BIND 9.16 and newer require a target libuv port. The
  current port uses BIND's supported non-threaded event loop because Pedigree
  does not yet implement `sigwait()` or `sigsuspend()`.
- OpenSSL is deliberately held at 3.5.8 on the 3.5 LTS line to retain the
  mature 3.x ABI instead of moving the catalog to the 4.x ABI.
- Legacy compatibility ports are pinned at their final upstream releases:
  PCRE1 8.45 and standalone ATK 2.38.0. New code should use PCRE2 instead of
  PCRE1.

## Disabled and deferred ports

The package loader omits the 15 recipes that define `DISABLED_REASON`. These
entries remain in-tree so their missing contracts and prerequisites stay
explicit.

| Port | Deferred version | Reason |
| --- | --- | --- |
| dosbox | 0.82.2 | DOSBox Staging 0.82.2 requires a functional SDL2 video, input, and audio frontend; the current Pedigree SDL2 compatibility profile is intentionally offscreen-only. Its mandatory static build dependencies iir, opusfile (plus opus and ogg), and SpeexDSP are also not yet in the FHS package catalog. zlib and libpng are already available. |
| fuse | 3.18.2 | libfuse 3.18.2 is a userspace half of the FUSE protocol, not a standalone filesystem layer. Pedigree provides neither `/dev/fuse` nor the matching kernel protocol ABI, and no target consumer can exercise the library without them. |
| grub2 | 2.14 | GNU GRUB 2.14 is a host-side boot-image tool, not a Pedigree target package. The current image build consumes checked-in GRUB Legacy 0.97 `stage2_eltorito` files and has no GRUB 2 host-tool or image-generation contract to package here. |
| libbind | 6.0 | ISC libbind 6.0 is the final standalone release and duplicates musl's resolver implementation. Its install replaces global `resolv.h`, `netdb.h`, and `arpa/nameser.h` headers; no active port requires that conflicting ABI, so it cannot safely share the target sysroot. |
| llvm | 22.1.8 | LLVM 22.1.8 is the current stable release, but Pedigree uses it only as a host analysis toolchain. Pedigree's maintained target compiler family is GCC, and LLVM has no Pedigree triple/driver, runtime, resource-directory, or target install contract. |
| netsurf | 3.11 | NetSurf 3.11 has no Pedigree frontend or HOST definition. Its generic framebuffer frontend uses libnsfb, whose only SDL surface still targets SDL 1.2; the RAM surface has no display or input. The full source build also requires separately staged NetSurf component libraries, including libcss, libdom, libnsfb, libnsutils, and their build system. |
| newlib | 4.6.0.20260123 | Pedigree's supported C library and final sysroot ABI is musl. GCC's stage-one `--with-newlib` flag only describes a compiler built before headers exist; the bootstrap does not build or install newlib, so a newlib target package would introduce a second incompatible libc. |
| pedigree-base | 0.1 | The main build still owns `images/base` and translates that tree to FHS only while composing a disk image. It does not publish a versioned FHS staging root, so packaging the mounted checkout as legacy version 0.1 would produce mutable, untraceable PUP contents. |
| pedigree-devel | 0.1 | The main build has no CMake install target or versioned SDK/sysroot export. Its bootstrap stages musl into the target sysroot while libgcc and libstdc++ remain owned by the compiler prefix; copying build-tree headers, CRT objects, or libraries would violate that boundary. |
| pedigree-kernel | 0.1 | The main `boot-artifacts` target builds `kernel-mini64` and its diagnostic kernel, but is explicitly an aggregate build target rather than an installer or staging directory. A versioned `/boot` export and an agreed debug-file destination are required before this can be a PUP package. |
| pedigree-modules | 0.1 | The main `boot-artifacts` target now builds `src/modules/initrd.tar` and a deterministic `initrd.manifest`, but it does not install or version that artifact. The package must consume an explicit module/initrd export instead of copying a mutable build directory. |
| prboom | 2.6.66 | PrBoom+ 2.6.66 is the final release of the archived upstream. A playable port requires a functional Pedigree SDL2 video and input frontend; the current compatibility profile is offscreen-only. Its cross build also requires a native first stage to export the WAD generator targets before compiling the Pedigree executable. |
| pth | 2.0.7 | GNU Pth 2.0.7 calls `sigpending()` throughout its scheduler and `sigsuspend()` both there and while bootstrapping signal-stack contexts. Pedigree exports both functions only as `ENOSYS` stubs, and no active port depends on Pth; replacing those calls with fake semantics is unsafe. |
| python27 | 2.7.18 | Python 2.7.18 is the final Python 2 release and is end-of-life. No active package requires it; depend on `python3` instead, which also provides `/usr/bin/python` for the target compatibility command. |
| qemu | 11.1.1 | QEMU 11.1.1 is a native host emulator used to run Pedigree, not software for the Pedigree root filesystem. It belongs in the local host tooling layer and has no target package or runtime contract. |

## Evidence boundary

At the 2026-09-02 modernization snapshot:

- All 277 unit tests invoked by `./runtests.sh` pass, and its Python syntax
  checks complete successfully.
- All 38 focused PUP repository-service tests pass with the pinned App Engine
  and Flask dependencies.
- All 69 active recipes have exact versioned build roots, completion markers,
  and PUP archives that pass the full Docker artifact audit. All 69 artifacts
  were published to the origin catalog with runtime dependency metadata.
- Server version `pup-http-cdn-20260902` was promoted, and Python 3 PUP wheel
  serial 10 was published and verified.
- An independent origin re-download matched the digest of all 69 published
  archives, covering 351,615,019 bytes in total.
- PUP, Mesa, binutils, GCC, mandoc, man-db, S-Lang, SDL2, APR, APR-util, and
  Apache all cross-build, stage, package, and audit successfully.
- A separate whole-catalog scan found no path-ownership or directory-mode
  conflicts and no unresolved, ambiguous, or undeclared target ELF runtime
  library providers across 769 target ELFs and 1,426 `DT_NEEDED` edges.
- A semantic symbol sweep checked those ELFs and all 87 active archives against
  95 known-unavailable target interfaces; every remaining reference is locally
  satisfied, advisory, diagnostic, or has an explicit failure fallback, with
  no unhandled reachable blocker.
- Python 3.14.7 and CMake 4.4.3 both cross-build, stage, package, and audit
  successfully. CMake includes the Pedigree platform modules and uses the
  staged OpenSSL and CA configuration.
- The new runtime profiles are deliberately bounded: Mesa is shared-only
  OSMesa/softpipe, SDL2 is static dummy/offscreen, and Apache is a runtime-only,
  no-DSO profile that supports only `httpd -X` until target file locking works.
- No target-runtime validation is claimed; the built binaries were not
  executed on Pedigree, and GCC was not run on target or used for a
  self-hosting rebuild.
- Origin publication and verification are complete. The public repository now
  serves immutable package archives from private Google Cloud Storage through
  Cloud CDN; catalog, wheel, and control routes remain on App Engine. All 187
  current and historical package objects were mirrored and verified.
