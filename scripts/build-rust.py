#!/usr/bin/env python3
"""Provision pinned Rust tools and build the Pedigree Linux-ABI baseline."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import tarfile
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
PINS = json.loads((ROOT / "language-ports/rust-toolchain.json").read_text())
VERSION = PINS["version"]
TARGET = PINS["target"]
RIPGREP_VERSION = "15.2.0"
RIPGREP_SOURCE = {
    "url": "https://codeload.github.com/BurntSushi/ripgrep/tar.gz/refs/tags/15.2.0",
    "sha256": "7605249d3eb0d5f170e3414498e3344e26b1e7a147aec518b57090b80036a562",
}
FLAGS = [
    "-C", "linker=rust-lld", "-C", "relocation-model=static",
    "-C", "target-feature=+crt-static", "-C", "link-self-contained=yes",
    # Pedigree reserves addresses below 4 MiB. LLD defaults to 2 MiB.
    "-C", "link-arg=--image-base=0x400000",
    "-C", "link-arg=-z", "-C", "link-arg=max-page-size=4096",
    "-C", "link-arg=-z", "-C", "link-arg=separate-loadable-segments",
]


def digest(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def host_target():
    target = {
        ("Darwin", "arm64"): "aarch64-apple-darwin",
        ("Darwin", "x86_64"): "x86_64-apple-darwin",
        ("Linux", "x86_64"): "x86_64-unknown-linux-gnu",
    }.get((platform.system(), platform.machine()))
    if target is None:
        raise RuntimeError("use the amd64 Docker builder on this host")
    return target


def fetch(pin, filename, cache, offline):
    destination = cache / "downloads" / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and digest(destination) == pin["sha256"]:
        return destination
    if offline:
        raise RuntimeError("missing or invalid cached download: " + str(destination))
    temporary = destination.with_suffix(destination.suffix + ".partial")
    try:
        print("Downloading " + pin["url"], flush=True)
        with urllib.request.urlopen(pin["url"], timeout=120) as source:
            with temporary.open("wb") as output:
                shutil.copyfileobj(source, output)
        if digest(temporary) != pin["sha256"]:
            raise RuntimeError("SHA-256 mismatch for " + pin["url"])
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def component(name, target, cache, offline):
    pin = PINS["components"][name][target]
    archive = fetch(pin, pin["url"].rsplit("/", 1)[1], cache, offline)
    destination = cache / "extract" / archive.name.removesuffix(".tar.xz")
    marker = destination / ".pedigree-sha256"
    if not marker.is_file() or marker.read_text().strip() != pin["sha256"]:
        shutil.rmtree(destination, ignore_errors=True)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as source:
            source.extractall(destination.parent, filter="data")
        marker.write_text(pin["sha256"] + "\n")
    return destination


def provision(cache, offline):
    host = host_target()
    prefix = cache / ("rust-" + VERSION + "-" + host)
    wanted = [("rustc", host), ("cargo", host), ("rust-std", host),
              ("rust-std", TARGET), ("rust-src", "*")]
    marker = prefix / ".pedigree-toolchain.json"
    identity = json.dumps({"pins": PINS, "host": host}, sort_keys=True)
    if marker.is_file() and marker.read_text() == identity:
        write_wrappers(prefix)
        return prefix
    marker.unlink(missing_ok=True)
    for name, target in wanted:
        source = component(name, target, cache, offline)
        # Each verified component already has its installed directory layout.
        # The global installer starts several shells per source file; copying
        # into this private prefix avoids that cost on Docker bind mounts.
        for entry in (source / "components").read_text().splitlines():
            if not entry or "/" in entry or entry in (".", ".."):
                raise RuntimeError("invalid Rust component name: " + repr(entry))
            payload = source / entry
            shutil.copytree(payload, prefix, dirs_exist_ok=True, symlinks=True,
                            ignore=lambda directory, names: ["manifest.in"]
                            if Path(directory) == payload else [])
    marker.write_text(identity)
    write_wrappers(prefix)
    return prefix


def write_wrappers(prefix):
    bindir = prefix / "bin"
    flags = " ".join(shlex.quote(flag) for flag in FLAGS)
    wrappers = {
        "pedigree-rustc": 'exec "$rust_bindir/rustc" --target=' + TARGET + " " + flags + ' "$@"\n',
        "pedigree-cargo": "export CARGO_BUILD_TARGET=" + TARGET + "\n"
            "export CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_RUSTFLAGS=" + shlex.quote(" ".join(FLAGS)) + "\n"
            'export RUSTC="$rust_bindir/rustc"\nexec "$rust_bindir/cargo" "$@"\n',
    }
    for name, command in wrappers.items():
        path = bindir / name
        path.write_text('#!/bin/sh\nset -eu\nrust_bindir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n' + command)
        path.chmod(0o755)


def environment(prefix, cache):
    env = os.environ.copy()
    env["PATH"] = str(prefix / "bin") + os.pathsep + env.get("PATH", "")
    env["RUSTC"] = str(prefix / "bin/rustc")
    env["CARGO_HOME"] = str(cache / "cargo-home")
    env["CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_RUSTFLAGS"] = " ".join(FLAGS)
    # Parent package-builder C flags are for Pedigree, but build scripts and
    # proc macros execute on the build host.
    for name in ("CC", "CXX", "AR", "CFLAGS", "CXXFLAGS", "LDFLAGS", "RUSTFLAGS"):
        env.pop(name, None)
    return env


def build_probe(prefix, cache, output):
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(prefix / "bin/rustc"), "--edition=2024", "--target", TARGET,
                    *FLAGS, "-C", "opt-level=2", "-C", "debuginfo=0",
                    "--remap-path-prefix=" + str(ROOT) + "=/usr/src/pedigree-apps",
                    str(ROOT / "language-ports/rust-probe/main.rs"),
                    "-o", str(output / "rust-probe")], check=True)


def build_ripgrep(prefix, cache, output, offline, source=None):
    if source is None:
        archive = fetch(RIPGREP_SOURCE, "ripgrep-15.2.0.tar.gz", cache, offline)
        source = cache / "src/ripgrep-15.2.0"
        shutil.rmtree(source, ignore_errors=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as bundle:
            bundle.extractall(source.parent, filter="data")
        subprocess.run(["patch", "-p1", "-i", str(ROOT / "packages/ripgrep/patches/optional-jemalloc.diff")],
                       cwd=source, check=True)
    env = environment(prefix, cache)
    env["GIT_CEILING_DIRECTORIES"] = str(source.parent)
    env["CARGO_TARGET_DIR"] = str(cache / "cargo-target/ripgrep-15.2.0" / host_target())
    vendor = cache / "vendor/ripgrep-15.2.0"
    lock_hash = digest(source / "Cargo.lock")
    marker = vendor / ".pedigree-lock-sha256"
    cargo = str(prefix / "bin/cargo")
    if not marker.is_file() or marker.read_text().strip() != lock_hash:
        if offline:
            raise RuntimeError("ripgrep dependency closure is not cached; run without --offline first")
        subprocess.run([cargo, "vendor", "--locked", str(vendor)],
                       cwd=source, env=env, check=True)
        marker.write_text(lock_hash + "\n")
    config = cache / "cargo-config" / ("ripgrep-" + host_target() + ".toml")
    config.parent.mkdir(parents=True, exist_ok=True)
    with config.open("w") as out:
        out.write('\n[source.crates-io]\nreplace-with = "vendored-sources"\n'
                  '[source.vendored-sources]\ndirectory = ' + json.dumps(str(vendor)) + '\n')
    subprocess.run([cargo, "--config", str(config), "build", "--offline", "--locked", "--release",
                    "--target", TARGET, "--no-default-features", "--bin", "rg"],
                   cwd=source, env=env, check=True)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(env["CARGO_TARGET_DIR"]) / TARGET / "release/rg", output / "rg")
    shutil.copy2(source / "Cargo.lock", output / "ripgrep-Cargo.lock")
    (output / "ripgrep-build.json").write_text(json.dumps({
        "version": RIPGREP_VERSION, "rust": VERSION, "target": TARGET,
        "source": RIPGREP_SOURCE, "cargo_lock_sha256": lock_hash,
        "patch_sha256": digest(ROOT / "packages/ripgrep/patches/optional-jemalloc.diff"),
        "binary_sha256": digest(output / "rg"), "rustflags": FLAGS,
        "allocator": "musl", "pcre2": False,
    }, indent=2) + "\n")


def stage_native(cache, output, offline, normalize, strip_tool=None):
    usr = output / "usr"
    (usr / "bin").mkdir(parents=True, exist_ok=True)
    compiler = component("rustc", TARGET, cache, offline) / "rustc"
    for relative in ["bin/rustc", "bin/rustdoc", "lib/rustlib/" + TARGET + "/bin/rust-lld"]:
        destination = usr / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(compiler / relative, destination)
    for path in (compiler / "lib").glob("*.so"):
        shutil.copy2(path, usr / "lib" / path.name)
    cargo = component("cargo", TARGET, cache, offline) / "cargo"
    shutil.copy2(cargo / "bin/cargo", usr / "bin/cargo")
    shutil.copytree(cargo / "share/doc/cargo", usr / "share/doc/cargo", dirs_exist_ok=True)
    standard = component("rust-std", TARGET, cache, offline) / ("rust-std-" + TARGET)
    shutil.copytree(standard / "lib", usr / "lib", dirs_exist_ok=True)
    shutil.copytree(compiler / "share/doc/rust", usr / "share/doc/rust", dirs_exist_ok=True)
    shutil.copytree(ROOT / "packages/rust/licenses", usr / "share/doc/rust/licenses", dirs_exist_ok=True)
    shutil.copy2(ROOT / "packages/rust/README.md", usr / "share/doc/rust/PEDIGREE.md")
    pin = PINS["native_libgcc"]
    archive = fetch(pin, pin["url"].rsplit("/", 1)[1], cache, offline)
    with tarfile.open(archive) as bundle:
        library = bundle.extractfile("usr/lib/libgcc_s.so.1")
        (usr / "lib/libgcc_s.so.1").write_bytes(library.read())
    (usr / "lib/libgcc_s.so.1").chmod(0o755)
    if normalize:
        patchelf = shutil.which("patchelf")
        if not patchelf:
            raise RuntimeError("native package normalization requires host patchelf")
        for relative in ("bin/rustc", "bin/rustdoc", "bin/cargo", "lib/rustlib/" + TARGET + "/bin/rust-lld"):
            subprocess.run([patchelf, "--set-interpreter", "/usr/lib/ld-musl-x86_64.so.1",
                            str(usr / relative)], check=True)
        subprocess.run([patchelf, "--replace-needed", "libc.musl-x86_64.so.1", "libc.so",
                        str(usr / "lib/libgcc_s.so.1")], check=True)
        (usr / "lib/libc.musl-x86_64.so.1").unlink(missing_ok=True)
    else:
        # Alpine names the same musl ABI differently. Keep the SDK libc as
        # the single provider when trying the unmodified upstream bootstrap.
        alias = usr / "lib/libc.musl-x86_64.so.1"
        if not alias.is_symlink():
            alias.symlink_to("libc.so")
    strip_version = None
    if strip_tool:
        strip_version = subprocess.check_output([strip_tool, "--version"], text=True).splitlines()[0]
        binaries = [usr / "bin/rustc", usr / "bin/rustdoc", usr / "bin/cargo",
                    usr / "lib/rustlib" / TARGET / "bin/rust-lld"]
        libraries = sorted(path for path in usr.rglob("*.so") if path.is_file())
        subprocess.run([strip_tool, "--strip-debug", *map(str, binaries + libraries)], check=True)
    provenance = dict(PINS, native_processing={
        "normalized": normalize, "strip_debug": strip_version,
    })
    (usr / "share/doc/rust/bootstrap-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    for name in ("pedigree-rustc", "pedigree-cargo"):
        destination = usr / "bin" / name
        shutil.copy2(ROOT / "language-ports/rust-probe" / name, destination)
        destination.chmod(0o755)
    shutil.copy2(ROOT / "language-ports/rust-probe/pedigree-cargo.toml",
                 usr / "lib/rustlib/pedigree-cargo.toml")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("provision", "probe", "ripgrep", "native", "all"))
    parser.add_argument("--cache", type=Path, default=ROOT / ".build/language-ports")
    parser.add_argument("--output", type=Path, default=ROOT / ".build/language-ports/artifacts")
    parser.add_argument("--source", type=Path, help="already patched ripgrep source root")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--normalize-native", action="store_true",
                        help="use patchelf to normalize the experimental native package")
    parser.add_argument("--native-strip", metavar="PROGRAM",
                        help="strip native debug sections using a host GNU cross-strip tool")
    args = parser.parse_args()
    cache, output = args.cache.resolve(), args.output.resolve()
    if args.action == "native":
        stage_native(cache, output, args.offline, args.normalize_native, args.native_strip)
        return
    prefix = provision(cache, args.offline)
    print("Rust cross toolchain: " + str(prefix), flush=True)
    if args.action in ("probe", "all"):
        build_probe(prefix, cache, output)
    if args.action in ("ripgrep", "all"):
        build_ripgrep(prefix, cache, output, args.offline,
                      args.source.resolve() if args.source else None)


if __name__ == "__main__":
    main()
