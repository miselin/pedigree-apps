# Go for Pedigree

This port provides Go 1.26.5 for `pedigree/amd64`, with a host cross compiler,
a target compiler distribution, and runtime and native-build qualification
programs. It uses Pedigree's Linux syscall ABI and builds static executables.
Cgo, the race detector, and signal-based asynchronous preemption are disabled.

Build the cross compiler and stage the native distribution:

```sh
./scripts/build-go-pedigree.sh
```

The script verifies the source and bootstrap archive checksums and prints the
cross-compiler wrapper, native root, and runtime-probe paths. Linux and macOS
hosts, on amd64 or arm64, have separate compiler and cache directories under
`.build/language-ports/go`. Set `PEDIGREE_GO_BUILD_DIR` to move these outputs,
or `GOROOT_BOOTSTRAP` to use an existing Go 1.24.6 or newer installation.

For example, on macOS arm64:

```sh
.build/language-ports/go/darwin-arm64/bin/pedigree-go build -o application .
```

The wrapper selects `GOOS=pedigree GOARCH=amd64 CGO_ENABLED=0`. Dependencies
must be available locally or downloaded by the host build. Linux build tags
and `_linux.go` source names also match this target; packages that inspect
`runtime.GOOS` explicitly may need a Pedigree case.

Build the target PUP through the standard package builder:

```sh
./buildPackages.sh --only go
./buildPackages.sh --only go --audit-only
```

Go ports built in that container can call the host wrapper at
`.build/x86_64/language-ports/go/linux-amd64/bin/pedigree-go` after building
the `go` package. The target package installs `/usr/bin/go`, `/usr/bin/gofmt`,
and `/usr/bin/go-qualify`, with the native tools and standard-library source
under `/usr/lib/go`. It has no additional target-library dependency for pure
Go builds; `ca-certificates` supplies trust roots for HTTPS module downloads.
The source distribution retains generated sources, but omits
upstream test fixtures, source tests, regeneration scripts, and cgo/race
objects for other systems.

Run `/usr/bin/go-qualify all` on Pedigree to check goroutines and GC, files,
pipes, timers, Unix and TCP sockets, entropy, and child processes. Individual
checks can be selected by name. `suite.json` supplies this probe to the QEMU
qualification harness; `native-suite.json` also installs the compiler root.

The native suite requires the current Bash and coreutils packages and their
runtime dependencies. Build that image baseline once before using the suite:

```sh
./buildPackages.sh --only-depends bash coreutils
```

The suite installs those staged roots, including readline, ncurses, and GMP.
Older image shells can mishandle absolute executable paths after a directory
change and cannot qualify the native compiler workflow.

The native compiler check runs offline and starts with an empty build cache:

```sh
sh /usr/share/go/native-smoke/run.sh
```

It compiles and tests a small word-count program, then builds and executes it
with known input. This exercises the compiler, assembler, linker, standard
library, test runner, and process execution on the running kernel. It is a
bring-up check; it does not establish that the upstream Go test suite passes.

All eight runtime checks pass in QEMU with one and four virtual CPUs. The
native compiler check passes against a Linux reference kernel. In Pedigree,
the `go` command and compiler subprocess start. Initial dependency-loading
attempts reached kernel OOM in both 2 GiB and 4 GiB guests. A kernel cache
metadata defect has since been repaired: the 256-file reproducer now uses
about 5.1 MiB instead of 516 MiB, and the native dependency walk now passes
in a 2 GiB guest. The repaired-kernel suite then timed out during the cold
native build at its 900-second overall limit, without an OOM. Native
compile/test/run remains unqualified; see [`docs/language-ports.md`](../../docs/language-ports.md)
for the retained diagnostics.

The target uses a 44-bit heap address range because Pedigree allocates dynamic
user mappings below 16 TiB. This keeps randomized heap hints in that range
and avoids page-summary reservations larger than the kernel's current
256 MiB mapping-replacement limit. The poll-based network backend remains
in use until an epoll-based Go runtime has separate qualification. Large
individual mappings, cgo, race instrumentation, and asynchronous preemption
need further work before enabling them.
