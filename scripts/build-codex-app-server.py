#!/usr/bin/env python3
"""Cross-build the pinned Codex App Server with the Pedigree Linux-musl ABI."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
REVISION = "694b6319d3ad2399f6e435760a22d9b9357f0697"
SOURCE = {
    "url": "https://codeload.github.com/openai/codex/tar.gz/" + REVISION,
    "sha256": "a7be863aed08b3ad8359e4338f81585773182dc6e4cb67c993d534d253e6cac4",
}
PATCH = ROOT / "packages/codex-app-server/patches/pedigree.diff"
PINS = json.loads((ROOT / "language-ports/codex-app-server/toolchain.json").read_text())
UAPI = json.loads((ROOT / "language-ports/codex-app-server/linux-uapi.json").read_text())
spec = importlib.util.spec_from_file_location("rust_build", ROOT / "scripts/build-rust.py")
rust = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rust)


def source_tree(cache, offline):
    archive = rust.fetch(SOURCE, "codex-" + REVISION + ".tar.gz", cache, offline)
    source = cache / "source" / ("codex-" + REVISION)
    marker = source / ".pedigree-patch-sha256"
    patch_hash = rust.digest(PATCH)
    if not marker.is_file() or marker.read_text().strip() != patch_hash:
        shutil.rmtree(source, ignore_errors=True)
        source.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(archive) as bundle:
            bundle.extractall(source.parent, filter="data")
        subprocess.run(["patch", "-p1", "-i", str(PATCH)], cwd=source, check=True)
        marker.write_text(patch_hash + "\n")
    return source


def build(cache, output, source, offline, jobs):
    if rust.host_target() != "x86_64-unknown-linux-gnu":
        raise RuntimeError("build this port in the linux/amd64 Docker builder")
    prefix = rust.provision(cache / "toolchain", offline, PINS)
    headers_archive = rust.fetch(UAPI, UAPI["url"].rsplit("/", 1)[1], cache, offline)
    headers = cache / ("linux-headers-" + UAPI["version"])
    headers_marker = headers / ".pedigree-sha256"
    if not headers_marker.is_file() or headers_marker.read_text().strip() != UAPI["sha256"]:
        shutil.rmtree(headers, ignore_errors=True)
        headers.mkdir(parents=True)
        with tarfile.open(headers_archive, ignore_zeros=True) as bundle:
            members = [m for m in bundle.getmembers() if m.isfile() and
                       m.name.startswith(("usr/include/linux/", "usr/include/asm/", "usr/include/asm-generic/"))]
            bundle.extractall(headers, members=members, filter="data")
        if not (headers / "usr/include/linux/random.h").is_file():
            raise RuntimeError("Linux UAPI archive is missing random.h")
        headers_marker.write_text(UAPI["sha256"] + "\n")
    source = source_tree(cache, offline) if source is None else source
    workspace = source / "codex-rs"
    env = rust.environment(prefix, cache)
    env["GIT_CEILING_DIRECTORIES"] = str(source.parent)
    env["CARGO_TARGET_DIR"] = str(cache / "target")
    env["CARGO_NET_GIT_FETCH_WITH_CLI"] = "true"
    env["CARGO_INCREMENTAL"] = "0"
    env["CARGO_BUILD_JOBS"] = str(jobs)
    env["CARGO_PROFILE_RELEASE_DEBUG"] = "0"
    env["CARGO_PROFILE_RELEASE_LTO"] = "false"
    env["CARGO_PROFILE_RELEASE_STRIP"] = "symbols"
    env["CARGO_PROFILE_RELEASE_CODEGEN_UNITS"] = "16"
    # An explicit pkg-config from the package environment must not select host
    # libraries for the bundled musl dependencies.
    env["PKG_CONFIG_ALLOW_CROSS_x86_64_unknown_linux_musl"] = "0"
    # C dependencies must select the same Linux ABI as Rust, without searching
    # the build host's libc headers.
    cflags = "-D__linux__=1 -isystem " + str(headers / "usr/include")
    env["CFLAGS_x86_64_unknown_linux_musl"] = cflags
    env["CXXFLAGS_x86_64_unknown_linux_musl"] = cflags
    env["AWS_LC_SYS_NO_JITTER_ENTROPY"] = "1"
    env["AWS_LC_SYS_NO_JITTER_ENTROPY_x86_64_unknown_linux_musl"] = "1"
    for variable, program in (("CC", "gcc"), ("CXX", "g++"), ("AR", "ar")):
        tool = shutil.which("x86_64-pedigree-" + program)
        if tool is None:
            raise RuntimeError("missing Pedigree cross tool: " + program)
        env[variable + "_x86_64_unknown_linux_musl"] = tool
    # Exposing the SDK library directories would also select its native libc
    # before Rust's Linux-musl libc, including its older syscall translation.
    native_runtime = cache / "native-runtime"
    shutil.rmtree(native_runtime, ignore_errors=True)
    native_runtime.mkdir()
    native_hashes = {}
    for compiler, library in (("gcc", "libgcc.a"), ("g++", "libstdc++.a")):
        path = subprocess.check_output(
            ["x86_64-pedigree-" + compiler, "-print-file-name=" + library], text=True
        ).strip()
        if not Path(path).is_file():
            raise RuntimeError("missing target runtime archive: " + path)
        shutil.copy2(path, native_runtime / library)
        native_hashes[library] = rust.digest(native_runtime / library)
    flags = rust.FLAGS + ["-Lnative=" + str(native_runtime)]
    env["CARGO_TARGET_X86_64_UNKNOWN_LINUX_MUSL_RUSTFLAGS"] = " ".join(flags)
    cargo = str(prefix / "bin/cargo")
    vendor = cache / "vendor"
    vendor_config = cache / "vendor.toml"
    marker = vendor / ".pedigree-lock-sha256"
    lock_hash = rust.digest(workspace / "Cargo.lock")
    if not marker.is_file() or marker.read_text().strip() != lock_hash or not vendor_config.is_file():
        if offline:
            raise RuntimeError("dependency closure is not cached; run without --offline first")
        with vendor_config.open("w") as config:
            subprocess.run([cargo, "vendor", "--locked", "--versioned-dirs", str(vendor)],
                           cwd=workspace, env=env, stdout=config, check=True)
        marker.write_text(lock_hash + "\n")
    # The generated vendor configuration may have moved with a copied cache.
    subprocess.run([cargo, "--config", str(vendor_config), "--config",
                    "source.vendored-sources.directory=" + json.dumps(str(vendor)),
                    "build", "--offline", "--locked",
                    "--release", "--target", rust.TARGET, "-p", "codex-app-server",
                    "--bin", "codex-app-server", "--no-default-features", "--features", "pedigree"],
                   cwd=workspace, env=env, check=True)
    stage = output / "root"
    shutil.rmtree(stage, ignore_errors=True)
    binary = stage / "usr/libexec/codex-app-server"
    binary.parent.mkdir(parents=True)
    shutil.copy2(cache / "target" / rust.TARGET / "release/codex-app-server", binary)
    launcher = stage / "usr/bin/codex-app-server"
    launcher.parent.mkdir(parents=True)
    launcher.write_text('#!/bin/sh\nexec /usr/libexec/codex-app-server "$@"\n')
    launcher.chmod(0o755)
    defaults = stage / "usr/share/codex-app-server/defaults.toml"
    defaults.parent.mkdir(parents=True)
    shutil.copy2(workspace / "config/defaults.toml", defaults)
    docs = stage / "usr/share/doc/codex-app-server"
    docs.mkdir(parents=True)
    for name in ("LICENSE", "NOTICE"):
        shutil.copy2(source / name, docs / name)
    shutil.copy2(ROOT / "packages/codex-app-server/README.md", docs / "PEDIGREE.md")
    shutil.copy2(workspace / "Cargo.lock", docs / "Cargo.lock")
    shutil.copytree(ROOT / "language-ports/codex-app-server/licenses",
                    docs / "dependencies/gcc-runtime-15.3.0")
    # Release-level standard-library notices are outside the installed payload.
    std_archive = PINS["components"]["rust-std"][rust.TARGET]["url"].rsplit("/", 1)[1]
    std_release = cache / "toolchain/extract" / std_archive.removesuffix(".tar.xz")
    runtime_notices = [prefix / "share/doc/rust/COPYRIGHT-library.html"] + [
        std_release / name for name in ("COPYRIGHT", "LICENSE-MIT", "LICENSE-APACHE")
    ]
    for notice in runtime_notices:
        if not notice.is_file():
            raise RuntimeError("missing Rust runtime notice: " + str(notice))
    runtime_docs = docs / "dependencies" / ("rust-runtime-" + PINS["version"])
    runtime_docs.mkdir(parents=True)
    for notice in runtime_notices:
        shutil.copy2(notice, runtime_docs / notice.name)
        (runtime_docs / notice.name).chmod(0o644)
    # Static dependencies retain their own attribution beside the upstream notice.
    for crate in sorted(vendor.iterdir()):
        if not crate.is_dir():
            continue
        for notice in crate.rglob("*"):
            if notice.is_file() and notice.name.upper().startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE", "COPYRIGHT")):
                destination = docs / "dependencies" / crate.name / notice.relative_to(crate)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(notice, destination)
                destination.chmod(0o644)
    provenance = {
        "revision": REVISION, "source": SOURCE, "toolchain": PINS,
        "target": rust.TARGET, "patch_sha256": rust.digest(PATCH),
        "cargo_lock_sha256": lock_hash, "binary_sha256": rust.digest(binary),
        "rustflags": flags, "allocator": "musl", "code_mode_host": False,
        "linux_uapi": UAPI, "target_cflags": cflags,
        "native_runtime_sha256": native_hashes,
        "rust_musl_libc_sha256": rust.digest(
            prefix / "lib/rustlib" / rust.TARGET / "lib/self-contained/libc.a"),
        "c_compiler": subprocess.check_output([env["CC_x86_64_unknown_linux_musl"], "--version"], text=True).splitlines()[0],
        "release_profile": {"debug": 0, "lto": False, "strip": "symbols", "codegen_units": 16},
    }
    (docs / "build.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print("Codex App Server package root: " + str(stage), flush=True)


def state_probe(cache, output):
    host = rust.host_target()
    if host != "x86_64-unknown-linux-gnu":
        raise RuntimeError("compile the state probe in the linux/amd64 Docker builder")
    prefix = cache / "toolchain" / ("rust-" + PINS["version"] + "-" + host)
    marker = prefix / ".pedigree-toolchain.json"
    identity = json.dumps({"pins": PINS, "host": host}, sort_keys=True)
    if (not (prefix / "bin/rustc").is_file() or not marker.is_file()
            or marker.read_text() != identity):
        raise RuntimeError("state-probe requires the completed pinned toolchain cache; run build first")
    target_deps = cache / "target" / rust.TARGET / "release/deps"
    host_deps = cache / "target/release/deps"
    externs = []
    for crate in ("codex_state", "tokio"):
        matches = sorted(path for path in target_deps.glob("lib" + crate + "-*.rlib")
                         if path.is_file())
        if len(matches) != 1:
            found = ", ".join(path.name for path in matches) or "none"
            raise RuntimeError("state-probe requires exactly one cached " + crate
                               + " release rlib from a completed build; found: " + found
                               + ". Use a cache containing one matching build generation.")
        externs.extend(["--extern", crate + "=" + str(matches[0])])
    if not host_deps.is_dir() or not any(path.is_file() for path in host_deps.glob("libserde_derive-*.so")):
        raise RuntimeError("state-probe requires cached host procedural macros; run build first")
    native_runtime = cache / "native-runtime"
    libraries = {"libgcc.a", "libstdc++.a"}
    if (not native_runtime.is_dir()
            or {path.name for path in native_runtime.iterdir()} != libraries
            or any(not (native_runtime / name).is_file() for name in libraries)):
        raise RuntimeError("state-probe requires the isolated libgcc.a/libstdc++.a cache; run build first")
    output.mkdir(parents=True, exist_ok=True)
    binary = output / "codex-state-qualify"
    subprocess.run([str(prefix / "bin/rustc"), "--edition=2024", "--target", rust.TARGET,
                    *rust.FLAGS, "-C", "opt-level=2", "-C", "debuginfo=0", "-C", "strip=symbols",
                    "-Ldependency=" + str(target_deps), "-Ldependency=" + str(host_deps),
                    "-Lnative=" + str(native_runtime), *externs,
                    str(ROOT / "language-ports/codex-app-server/state-probe.rs"),
                    "-o", str(binary)], env=rust.environment(prefix, cache), check=True)
    print("Codex state probe: " + str(binary), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["build", "state-probe"])
    parser.add_argument("--source", type=Path, help="already patched pinned Codex source root")
    parser.add_argument("--output", type=Path, default=ROOT / ".build/codex-app-server/artifacts")
    parser.add_argument("--cache", type=Path, default=ROOT / ".build/codex-app-server")
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    cache = args.cache.resolve()
    if args.action == "state-probe":
        state_probe(cache, args.output.resolve())
    else:
        cache.mkdir(parents=True, exist_ok=True)
        build(cache, args.output.resolve(), args.source.resolve() if args.source else None,
              args.offline, args.jobs)


if __name__ == "__main__":
    main()
