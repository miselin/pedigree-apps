# Port status

The current catalog contains 58 active Pedigree ports and 23 explicit disabled
or deferred entries. An active entry is loadable by the package builder; it
does not by itself claim a completed integrated build or successful execution
on Pedigree.

## Local workflow

The maintained path is the local amd64 Docker builder described in
[`README.md`](README.md). It uses the current Pedigree cross-toolchain, stages
each package under `newpacks/x86_64/<package>/<version>/root`, and enforces the
target FHS layout, primarily under `/usr`, `/etc`, and `/var`. Builds are local
by default and do not upload unless an upload option is explicitly selected.

List the active catalog or inspect a dependency closure without building:

```sh
./buildPackages.sh --list
./buildPackages.sh --dry-run --only-depends python3
```

## Active catalog

| Port | Version | Port | Version | Port | Version |
| --- | --- | --- | --- | --- | --- |
| atk | 2.38.0 | autoconf | 2.73 | bash | 5.3.15 |
| bind | 9.11.37 | bsdtar | 3.8.9 | ca-certificates | 2026.08.13 |
| cairo | 1.18.4 | cmake | 4.4.3 | coreutils | 9.11 |
| curl | 8.22.0 | dialog | 1.3.20260721 | diffutils | 3.12 |
| dropbear | 2026.94 | e2fsprogs | 1.47.4 | expat | 2.8.4 |
| fontconfig | 2.18.3 | fribidi | 1.0.16 | gawk | 5.4.1 |
| gdbm | 1.26 | gettext | 1.0 | git | 2.55.0 |
| glib | 2.88.3 | gnumake | 4.4.1 | grep | 3.12 |
| gzip | 1.14 | harfbuzz | 14.4.0 | inetutils | 2.8 |
| less | 704 | libffi | 3.8.0 | libfreetype | 2.14.3 |
| libgmp | 6.3.0 | libiconv | 1.19 | libmpc | 1.4.1 |
| libmpfr | 4.2.2 | libpcre | 8.45 | libpcre2 | 10.48 |
| libpipeline | 1.5.8 | libpng | 1.6.58 | libtool | 2.6.2 |
| lua | 5.5.1 | lynx | 2.9.3 | m4 | 1.4.21 |
| mtools | 4.0.49 | nano | 9.2 | nasm | 3.02 |
| ncurses | 6.6 | openssl | 3.5.8 | pango | 1.58.2 |
| perl | 5.44.0 | pixman | 0.46.4 |  |  |
| python3 | 3.14.7 | readline | 8.3.3 | sed | 4.10 |
| sqlite | 3.53.4 | vim | 9.2.1031 | vttest | 20251205 |
| wget | 1.25.0 | zlib | 1.3.2 |  |  |

Python 3.14.7 replaces the disabled Python 2 recipe and also provides
`/usr/bin/python` as a compatibility link.

The `ca-certificates` port installs the versioned Mozilla-derived trust bundle
at `/etc/ssl/cert.pem` for the catalog's HTTPS clients.

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

The package loader omits the 23 recipes that define `DISABLED_REASON`. These
entries remain in-tree so their missing contracts and prerequisites stay
explicit.

| Port | Deferred version | Reason |
| --- | --- | --- |
| apache2 | 2.4.68 | Needs current APR and APR-util; APR-util is absent, and the old Apache recipe depended on a legacy layout and bundled APR trees. |
| apr | 1.7.6 | Pedigree lacks a selected process-shared mutex/shared-memory backend, and APR's libtool lacks the target integration needed beyond a static-only probe. |
| binutils | 2.46.1 | The builder supplies binutils. A self-hosted package needs the old Pedigree BFD, GAS, and linker changes rebased beyond 2.32 and validated separately. |
| dosbox | 0.74-3 | Requires SDL 1.2, which is absent from the FHS catalog; the old recipe also hard-coded a legacy `sdl-config` path. |
| fuse | 3.18.2 | Pedigree has no FUSE kernel protocol or `/dev/fuse`, and the historical entry had no implementation. |
| gcc | 16.2.0 | GCC 15.3.0 comes from the builder. Self-hosting GCC is a separate bootstrap and target-runtime project; the legacy GCC 8 path references missing old patches and obsolete Autotools. |
| grub2 | 2.12 | GRUB is a host boot-image tool, not a target-root package. The current i386-pc flow needs a native build contract and rebased platform patch. |
| llvm | 22.1.8 | The old placeholder has no Pedigree target, runtime, resource-directory, or staged-install integration for this host/self-hosting toolchain. |
| libbind | 6.0 | Duplicates musl's resolver API and would overwrite musl and BIND headers under the global FHS paths. No active port depends on it; revival needs namespaced headers and target resolver validation. |
| man-db | 2.13.1 | The catalog has no groff or mandoc provider, so `man` would lack the formatter needed for ordinary source manual pages. |
| mesa | 26.2.1 | The current Meson build has no Pedigree platform, WSI, DRM, or software-renderer integration; the Mesa 9.1 Autotools patches are not reusable as-is. |
| netsurf | 3.11 | The historical Pedigree framebuffer frontend and support paths were not carried into the current component build; a new frontend port is required. |
| newlib | 4.6.0.20260123 | Pedigree's supported C library and sysroot ABI is musl; the old placeholder had no source, build, or install recipe. |
| pedigree-base | 0.1 | References a removed source-tree image layout; it needs a versioned FHS base artifact exported by the main Pedigree build. |
| pedigree-devel | 0.1 | Emits legacy paths and duplicates old musl/CRT files; a replacement needs a maintained FHS sysroot export while keeping libstdc++ in the compiler prefix. |
| pedigree-kernel | 0.1 | References obsolete kernel and debug paths; it needs versioned FHS kernel and debug artifacts from the main build. |
| pedigree-modules | 0.1 | Assumes removed module, subsystem, driver, and initrd paths; it needs a versioned module/initrd export from the main build. |
| prboom | 2.5.0 | The unmaintained original release depends on missing SDL 1.2 and legacy paths; choosing a maintained Doom source port is separate work. |
| pth | 2.0.7 | Its scheduler, pending-signal bookkeeping, and signal-stack context creation require `sigpending()` and `sigsuspend()`, which Pedigree does not implement. No active port depends on it; revival needs target signal support or a validated replacement backend. |
| pup | 0.1 | The target updater is a Python 2 `setup.py` package for legacy paths; it needs a Python 3 port plus FHS and runtime-dependency contracts. |
| python27 | 2.7.3 | Python 2 is end-of-life. Use active `python3` 3.14.7, which also supplies `/usr/bin/python`. |
| qemu | 11.1.0 | QEMU is a native host emulator, not target-root software; it belongs in the local builder and tooling layer. |
| slang | 2.3.3 | The old entry was an empty placeholder; a port still needs a pinned source, cross-configure answers, ncurses integration, and target terminal validation. |

## Evidence boundary

At the 2026-09-02 modernization snapshot:

- All 165 host unit tests and static checks pass.
- All 58 active recipes have an exact versioned build root, completion marker,
  and PUP archive. The full Docker artifact audit passes for the complete
  active catalog.
- Python 3.14.7 and CMake 4.4.3 both cross-build, stage, package, and audit
  successfully. CMake includes the Pedigree platform modules and uses the
  staged OpenSSL and CA configuration.
- No target-runtime validation is claimed; neither Python nor CMake was
  executed on Pedigree during this sweep.
- No package upload has been performed.
