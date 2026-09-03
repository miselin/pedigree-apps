# pedigree-apps

> [!NOTE]
> This is the active development repository. It is receiving substantial
> AI-assisted maintenance to address long-standing bugs, modernize the tooling,
> and improve stability. For the pre-AI historical snapshot, see
> [`miselin/pedigree-apps-legacy`](https://github.com/miselin/pedigree-apps-legacy).

This repository contains application ports and the Pedigree UPdater (`pup`)
package tooling for [Pedigree](https://www.pedigree-project.org/).

The modernization catalog currently contains 69 active ports and 15 explicit
disabled or deferred entries. See [`PORTS.md`](PORTS.md) for the complete
version list, compatibility ceilings, deferrals, and the current verification
boundary.

At the 2026-09-02 snapshot, all 69 active ports have exact versioned build
roots, completion markers, and PUP archives that pass the full Docker artifact
audit. This is cross-build and packaging evidence; the binaries were not
executed on Pedigree during this sweep.

The maintained build path is local Docker. It uses Pedigree's current amd64
cross-toolchain and creates packages with the FHS layout used by the operating
system: `/usr/bin`, `/usr/lib`, `/usr/include`, `/etc`, `/var`, and
`/usr/share`.

## Build locally

Install Docker, then run builds from the repository root. No host Python
environment, chroot, or `sudo` setup is needed.

```sh
./buildPackages.sh --list
./buildPackages.sh
./buildPackages.sh --dry-run --only-depends cmake
./buildPackages.sh --only-depends libpng
```

With no package selection, the builder processes the complete active catalog.
`--only-depends` builds the requested packages and their transitive build
dependencies. `--only` builds only the named packages and expects their
dependency artifacts to exist already.

Audit completed artifacts without rebuilding or uploading:

```sh
./buildPackages.sh --audit-only
./buildPackages.sh --only zlib openssl --audit-only
```

The audit is read-only. It verifies each selected recipe's exact versioned
build root and completion marker, exact root-to-PUP payload match, archive
ownership and path safety, FHS paths and symlinks, and target ELF, archive,
interpreter, dynamic-path, and libtool metadata. It does not execute target
binaries, resolve `NEEDED` entries across packages, or establish Pedigree
runtime compatibility.

The first run builds `pedigree-apps-builder:local` from a pinned published
Pedigree builder image. Rebuild that derived image after changing its
Dockerfile, Python dependencies, or the bundled PUP source:

```sh
./buildPackages.sh --rebuild-image --only-depends cmake
```

The default parallelism is eight jobs. Override it when useful:

```sh
PEDIGREE_APPS_JOBS=4 ./buildPackages.sh --only cmake
```

CMake-based ports use a persistent compiler cache under `.build/ccache`.

Docker runs the amd64 builder explicitly, including on Apple Silicon hosts.
Only the amd64 Pedigree target is maintained by this workflow today.

## Build from the current Pedigree checkout

The default base image is pinned so repeated local builds start from the same
known toolchain. To test against a newer sibling `pedigree` checkout, build its
builder image first:

```sh
./scripts/build-pedigree-builder.sh
PEDIGREE_BUILDER_IMAGE=pedigree-builder:local \
  ./buildPackages.sh --rebuild-image --only-depends cmake
```

Set `PEDIGREE_SOURCE` if the Pedigree checkout is not at `../pedigree`:

```sh
PEDIGREE_SOURCE=/path/to/pedigree ./scripts/build-pedigree-builder.sh
```

This intentionally remains a local workflow. Reproducible release promotion
and automated builders can be layered on later without changing package build
hooks.

## Outputs

A successful build writes:

- staged FHS roots to `newpacks/x86_64/<package>/<version>/root`;
- PUP archives to `pup/package_repo`;
- source downloads to `downloads`;
- per-package build logs to `.build/x86_64/logs`.

Current revived examples include zlib 1.3.2, libpng 1.6.58, GNU Make 4.4.1,
CMake 4.4.3, mandoc 1.14.6, and man-db 2.13.1. The versioned
`ca-certificates` port provides the system trust bundle at `/etc/ssl/cert.pem`.
Updated ports use HTTPS downloads with pinned SHA-256 hashes. Target-native
binutils 2.46.1 and GCC 15.3.0 are active and pass the Docker artifact audit.
They are built with the existing Pedigree cross-toolchain; execution on
Pedigree and compiler self-hosting remain unverified.

## Publish explicitly

Local builds never upload by default. With a valid PUP upload key already in
the environment, upload completed artifacts explicitly without rebuilding:

```sh
./buildPackages.sh --only zlib --audit-only
./buildPackages.sh --only zlib --upload-only
```

Run the matching audit first: `--upload-only` checks that the root, completion
marker, and PUP exist, but it does not repeat the artifact audit.

Use `--upload` instead to build the complete selected wave first and upload it
only after every build succeeds. The wrapper runs the build without the key,
then starts a separate upload-only container so package build processes cannot
read the credential.

If `UPLOAD_KEY` is not already available, the publication helper retrieves it
from the legacy GCP project using an authenticated `gcloud` account:

```sh
./scripts/publish-packages.py zlib
./scripts/publish-packages.py --all
```

The helper audits the complete selection before retrieving the key, then
publishes packages in runtime-dependency order. It requires the repository to
advertise dependency-metadata support before requesting an upload URL and
verifies each selected catalog record and downloaded archive after upload. A
batch is not transactional: if a later package fails, packages already verified
by the helper remain published.

The direct build command exits before building if `UPLOAD_KEY` is not set. The
helper obtains the key without printing it or copying it into a command line.

## Package definitions

Each `packages/<name>/package.py` defines its source, checksum, dependency
metadata, patches, and build phases. Common Autoconf and CMake helpers install
under FHS paths and stage dependency roots for each package without modifying
the Pedigree toolchain sysroot.

The target image contract has a small package baseline: Bash supplies
`/usr/bin/bash`, the image's FHS aliases expose it as `/usr/bin/sh` and
`/bin/sh`, and coreutils provides `/usr/bin/env` plus the basic command-line
utilities used by package scripts.
Image assembly must install both packages and their declared runtime closures
before ordinary ports. Recipes therefore do not list `bash` or `coreutils` as
runtime dependencies; doing so would introduce cycles such as Bash -> Readline
-> ncurses -> shell. All other executable-script interpreters remain explicit:
for example, Autoconf and OpenSSL declare Perl, and GLib declares Python 3. The
builder checks this contract against staged executable scripts; documentation
examples are not treated as installed commands.

This baseline is an image-assembly invariant, not dependency information hidden
inside a PUP archive. Individual PUP archives remain payload-only tar files;
the repository catalog records each package's non-baseline runtime dependencies
and the client installs that closure in dependency-first order.

PUP 1.2 is also an active target port. It installs `/usr/bin/pup`, uses
`/etc/pup/pup.conf`, stores its local database and package cache under
`/var/lib/pup`, and declares Python 3 plus the system CA bundle as its runtime
closure. Its client accepts both dependency-aware and historical PUP v1 JSON
databases, verifies the legacy SHA-1 catalog digest before extracting an
archive, and detects missing or cyclic dependencies before installation. Use
`run_pup.sh` to run the host copy in the builder image when working with the
local repository by hand.

## Tests

Run the Python builder tests and syntax checks on the host:

```sh
./runtests.sh
```

For support, open an issue in this repository.
