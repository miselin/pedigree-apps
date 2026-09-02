# pedigree-apps

> [!NOTE]
> This is the active development repository. It is receiving substantial
> AI-assisted maintenance to address long-standing bugs, modernize the tooling,
> and improve stability. For the pre-AI historical snapshot, see
> [`miselin/pedigree-apps-legacy`](https://github.com/miselin/pedigree-apps-legacy).

This repository contains application ports and the Pedigree UPdater (`pup`)
package tooling for [Pedigree](https://www.pedigree-project.org/).

The maintained build path is local Docker. It uses Pedigree's current amd64
cross-toolchain and creates packages with the FHS layout used by the operating
system: `/usr/bin`, `/usr/lib`, `/usr/include`, `/etc`, `/var`, and
`/usr/share`.

## Build locally

Install Docker, then run builds from the repository root. No host Python
environment, chroot, or `sudo` setup is needed.

```sh
./buildPackages.sh --list
./buildPackages.sh --dry-run --only-depends cmake
./buildPackages.sh --only-depends libpng
```

`--only-depends` builds the requested packages and their transitive build
dependencies. `--only` builds only the named packages and expects their
dependency artifacts to exist already.

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
and CMake 4.4.3. Updated ports use HTTPS downloads with pinned SHA-256 hashes.
The legacy GCC 8 and MPC 0.8 recipes remain in-tree but are deferred because
they require obsolete host Autoconf and Automake versions; the Docker builder
supplies the maintained Pedigree cross-toolchain instead.

## Publish explicitly

Local builds never upload by default. With a valid PUP upload key already in
the environment, upload completed artifacts explicitly without rebuilding:

```sh
./buildPackages.sh --only cmake --upload-only
```

Use `--upload` instead to build the complete selected wave first and upload it
only after every build succeeds. The wrapper runs the build without the key,
then starts a separate upload-only container so package build processes cannot
read the credential.

If `UPLOAD_KEY` is not already available, the publication helper retrieves it
from the legacy GCP project using an authenticated `gcloud` account:

```sh
./scripts/publish-packages.py cmake gnumake zlib
```

The direct build command exits before building if `UPLOAD_KEY` is not set;
the helper obtains it without printing or copying it into a command line.
The legacy PUP service does not store runtime dependency metadata, so the
builder refuses to upload a package that declares runtime dependencies.

## Package definitions

Each `packages/<name>/package.py` defines its source, checksum, dependency
metadata, patches, and build phases. Common Autoconf and CMake helpers install
under FHS paths and stage dependency roots for each package without modifying
the Pedigree toolchain sysroot.

`pup` is also kept in this repository. Use `run_pup.sh` to run it in the same
builder image when working with the local repository by hand.

## Tests

Run the Python builder tests and syntax checks on the host:

```sh
./runtests.sh
```

For support, open an issue in this repository.
