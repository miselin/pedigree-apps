# Go and Rust on Pedigree

These ports target amd64. Go has a `pedigree/amd64` target; Rust initially uses
`x86_64-unknown-linux-musl` through Pedigree's Linux syscall ABI. Both provide
host tools for building applications, runtime probes, and separate native
compiler qualification suites.

## Qualification status

The initial guest evidence uses Pedigree commit
`192bf30cb55392ce6b1026d427b30b7545e1b524`. The cache-memory repair and native
Go retry use freshly rebuilt images with the source now committed as
`0139dd022`. Both builds use `PEDIGREE_CRIPPLE_HDD=TRUE`. Filesystem checks establish behavior during one
boot, including compiling into `/tmp`; they do not establish persistent disk
writeback. Host execution of a target ELF on Linux is not Pedigree qualification.

| Milestone | Current evidence |
| --- | --- |
| Go 1.26.5 cross compiler and target tools | Built from the pinned Go source with the local Pedigree patch. |
| Go runtime, one and four CPUs | Passed all eight checks: allocation/GC and goroutines, files, pipes, timers, Unix sockets, TCP loopback, entropy, and child execution with redirected input/output. The one-CPU runtime pass is the first case of the native suite. |
| Go native compiler | The packaged `go` command and its compiler child start. Native builds remain unqualified. The initial 2048 MiB build and 4096 MiB dependency-loading diagnostic reached kernel OOM; the kernel cache metadata defect is now fixed, and the same dependency walk now passes. The repaired-kernel suite then timed out during the cold native build at the 900-second overall limit, without an OOM. |
| Rust 1.85.1 standard-library runtime | Passed on one and four CPUs: basic execution, files, threads, child execution by absolute path, and TCP loopback. |
| ripgrep 15.2.0 | Built from source and passed version, file search, and recursive search with two worker threads on one and four CPUs. |
| Rust native compiler/Cargo | The normalized bootstrap starts both `rustc 1.85.1` and Cargo in one- and four-CPU QEMU. Native compilation did not complete within the 900-second direct trial or the 1200-second full suite; compile/run remains unqualified. |
| Docker package build and artifact audit | Go, Rust, and ripgrep PUPs built and passed the full artifact audit. The compiler packages are experimental. |

The kernel memory spike found roughly 2 MiB of cache-filter allocation per
first-touched inode. The repair reduces the 256-file QEMU probe from 516 MiB
to 5.1 MiB on both one and four CPUs. See
[the cache-memory report](cache-memory-spike.md) for the reproducer, regression
tests, and before/after evidence.

Initial compiler/runtime evidence is under `.build/language-qualification/`:

- `go-runtime-final-4cpu/`: clean Go runtime pass.
- `go-native-v2-1cpu/`: the exact Go package passed the runtime case, then the
  native build reached kernel OOM after 508 seconds; the overall suite failed.
- `go-native-diag-1cpu/`: compiler subprocess startup passed, then `go list
  -deps` reached kernel OOM after 447 seconds in a 4096 MiB guest. The final GC
  trace showed only about 3 MiB of Go heap before collection.
- `rust-package-1cpu/` and `rust-package-4cpu/`: all eight Rust/ripgrep cases
  passed using the exact final packaged ripgrep binary.
- `rust-native-v2-1cpu/`: rustc and Cargo versions passed; the compile case
  failed because its source fixture was hidden by the guest's `/tmp` mount.
  The checked-in suites correct that fixture path.
- `rust-native-v3-4cpu/` and `rust-native-combined-1cpu/`: subsequent native
  bootstrap attempts timed out during direct compilation. The combined run
  never reached its Cargo-build case.

The repaired-kernel retry is retained at `.build/memory-spike/go-native-1cpu/`.
It passed all eight runtime checks and `go list -deps -test .` in a 2048 MiB
guest before starting the cold native build. The overall suite reached its
900-second limit during that build without an OOM; it did not reach the
compile/test/run success marker. This is a dependency-loading pass, not native
compiler qualification.

The Go probe in the PUP is byte-for-byte identical to the four-CPU runtime
payload (`05cd8a35f031de6e8ea7ea1e51617084aa0f56196f13f20d18cddedcd2d6f5ea`).
All three PUP audits passed (`.build/language-pups-audit-final.log`), and the
repository regression suite passed 288 tests (`.build/memory-spike/apps-tests.log`).

Earlier failed experiments remain beside those runs. Each run's `metadata.json`
records its payload hashes, source image hashes, suite commands, and QEMU
configuration. `result.json` distinguishes successful qualification from image
preparation and failure.

The tested kernel's `Cache::timer` also restarts its sorted scan after each
dirty page, revisiting and checksumming preceding clean pages. With failed
writebacks under `PEDIGREE_CRIPPLE_HDD`, large resident compiler libraries can
be scanned repeatedly. Source inspection and the disk/cache keys establish
this mechanism; its share of the observed native-build time has not been
profiled. The excessive per-inode filter allocation has been repaired; cache
scanning remains a separate performance follow-up, along with qualification
on a write-enabled disposable disk.

## Build Go

```sh
./scripts/build-go-pedigree.sh
```

The script verifies source/bootstrap archive checksums, builds the host compiler
and Pedigree tools, and stages the native distribution. It supports macOS amd64
and arm64, and Linux amd64 and arm64. `GOROOT_BOOTSTRAP` can select an existing
bootstrap installation; `PEDIGREE_GO_BUILD_DIR` changes the output root.

The script prints the host-specific `pedigree-go` wrapper path. For example,
on the Linux amd64 builder:

```sh
.build/language-ports/go/linux-amd64/bin/pedigree-go build -o example ./example
```

On Apple Silicon the corresponding directory is `darwin-arm64`. The wrapper
sets `GOOS=pedigree`, `GOARCH=amd64`, and `CGO_ENABLED=0`. Native files are staged
under `.build/language-ports/go/native-root`, with `/usr/bin/go`,
`/usr/bin/gofmt`, and `/usr/lib/go` in the guest.

The local target uses a poll-based network runtime and disables asynchronous
signal preemption. Its 44-bit heap geometry matches Pedigree's user mapping
range and avoids oversized allocator metadata mappings. The current supported
build path is pure Go; cgo and race instrumentation are not qualified.

The native smoke project runs `go test`, compiles a multi-file word-count
program, and checks the resulting program's output. A host-generated compiler
binary alone does not pass that milestone.

## Build Rust and ripgrep

```sh
python3 scripts/build-rust.py all
```

This provisions pinned Rust 1.85.1 host tools, target `std`, and Rust library
sources, then builds `rust-probe` and ripgrep 15.2.0. Outputs default to
`.build/language-ports/artifacts`. Use `provision`, `probe`, or `ripgrep` in place
of `all` to select one step. `--cache` and `--output` select other directories.

After downloading the toolchain, ripgrep source, and vendored dependencies, the
build can be repeated with `--offline`. Cargo uses the release's `Cargo.lock`
and the verified vendored dependency closure. ripgrep uses the musl allocator;
optional jemalloc and PCRE2 are disabled in this initial port.

The Rust target retains upstream Linux-musl target metadata and its bundled
static libc. It is not yet a distinct Pedigree Rust target. The script's link
flags place the executable at or above `0x400000`, separate loadable segments,
and use 4096-byte maximum pages; retain these flags when adding another Rust
application. Pinned component URLs and hashes are in
[`rust-toolchain.json`](../language-ports/rust-toolchain.json).

The provisioner prints its host-specific toolchain directory, which contains
`bin/pedigree-rustc` and `bin/pedigree-cargo`. These wrappers select the target
and its required linker flags. For example, in the Linux amd64 builder:

```sh
.build/language-ports/rust-1.85.1-x86_64-unknown-linux-gnu/bin/pedigree-cargo build --release
```

Stage the experimental native compiler separately using the Linux builder:

```sh
docker run --rm --platform linux/amd64 -v "$PWD:/workspace" \
  pedigree-apps-builder:local python3 scripts/build-rust.py native \
  --normalize-native \
  --native-strip /opt/pedigree/bin/x86_64-pedigree-strip \
  --output .build/language-ports/artifacts/rust-native-normalized
```

This installs the upstream musl compiler, Cargo, target libraries, linker, and
pinned `libgcc_s` dependency into a guest root. Normalization requires host
`patchelf`, included in the Docker builder, and selects Pedigree's loader and
libc paths. The strip option removes debug sections and reproduces the tested
compiler payload. Guest `pedigree-rustc` and `pedigree-cargo` wrappers set the sysroot
and linker flags explicitly. The native suite must compile and execute
[`native.rs`](../language-ports/rust-probe/native.rs); the separate
`rust-native-cargo.json` suite builds the same threaded/filesystem program
through Cargo with an empty cache and no network access.

`std::env::current_exe()` is a known gap: `/proc/self/exe` is unavailable in the
tested guest. The passing process probe uses an explicit absolute executable
path. The separate capability suite keeps this gap visible without conflating
it with the qualified process behavior.

## Run the guest suites

Build fresh images in the main checkout after its builders and guests have
stopped:

```sh
cmake --build ../pedigree/build --target livecd hddimage -j2
```

Run each runtime suite on one and four CPUs, using a new output directory for
every invocation:

```sh
python3 scripts/qualify-language-ports.py \
  --iso ../pedigree/build/pedigree.iso --disk ../pedigree/build/hdd.img \
  --suite language-ports/go/suite.json \
  --cpus 1 --timeout 300 --output-dir .build/language-qualification/go-new-1cpu

python3 scripts/qualify-language-ports.py \
  --iso ../pedigree/build/pedigree.iso --disk ../pedigree/build/hdd.img \
  --suite language-ports/rust-runtime.json \
  --cpus 4 --timeout 300 --output-dir .build/language-qualification/rust-new-4cpu
```

Change `--suite` to `language-ports/go/native-suite.json` or
`language-ports/rust-native.json` for native compiler qualification. Use
`--timeout 1200` for a cold standard-library compilation. The Rust native tree
needs more free space than the current base image provides; add
`--disk-size-mib 4096` to grow its disposable copy. The default guest RAM is
2048 MiB; `--memory` overrides it.

The native suites include current base applications. Build their roots first:

```sh
./buildPackages.sh --only-depends bash coreutils
```

This matters for older images whose legacy shell predates the current FHS
package layout. Store injected source fixtures outside `/tmp`, `/dev`, `/proc`,
`/run`, and `/var/run`: guest mounts can hide files injected into those paths.

The runner requires QEMU and e2fsprogs (`debugfs`, plus `e2fsck` and `resize2fs`
when growing a disk). It clones the input images, verifies every injected file,
and uses QEMU snapshots. It captures COM1 output with no network interface;
guest loopback remains available. `--cpu max` supplies the hardware entropy
used by the entropy probe. `--prepare-only` verifies image preparation without
claiming guest execution.

The checked-in manifests use default build output paths. If build outputs move,
copy and adjust the suite's host `source` paths; those paths are resolved
relative to the manifest. Guest commands and required marker lines remain
explicit. Every case must return zero and emit its markers before the final
suite marker. A terminal failure stays failed while a short drain captures its
diagnostic tail.

## Package checks and remaining milestones

The recipes build or stage the same pinned toolchains used above:

```sh
./buildPackages.sh --rebuild-image --only go rust ripgrep
./buildPackages.sh --only go rust ripgrep --audit-only
./runtests.sh
```

Package checks cover staging and artifact integrity; QEMU suites cover actual
guest behavior. Keep both results with the release being qualified.
The archives are `pup/package_repo/go-1.26.5-amd64.pup`,
`rust-1.85.1-amd64.pup`, and `ripgrep-15.2.0-amd64.pup`. Install them through
PUP after adding them to a package catalog; installation is catalog-driven.
The Rust package includes `rustc`, Cargo,
`rustdoc`, the standard library, its runtime dependency, and the
`pedigree-rustc` / `pedigree-cargo` wrappers. Compiler startup is qualified;
native application compilation remains experimental. No packages have been
published by this work.

The next gates are completed native Go compile/test/run, Rust compile/run and
Cargo dependency builds in the guest, and durable
filesystem qualification with a write-enabled kernel and disposable disks.
Broader library tests, cgo, external networking/TLS, and a distinct Pedigree Rust
target remain separate work.
