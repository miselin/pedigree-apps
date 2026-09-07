#!/usr/bin/env python3
"""Build the standalone V8 embedding library in the amd64 ports container."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from support import steps

PINS = json.loads((ROOT / "language-ports/v8/source.json").read_text())
ARCHIVES = (
    "v8_snapshot", "v8_base_without_compiler", "v8_compiler",
    "v8_initializers", "v8_initializers_slow", "v8_libplatform", "v8_libbase",
    "v8_zlib", "highway", "simdutf", "abseil",
)
CONFIGURE = (
    "--cross-compiling", "--dest-os=linux", "--dest-cpu=x64", "--without-intl",
    "--without-ssl", "--without-inspector", "--without-node-snapshot",
    "--without-node-code-cache", "--without-amaro", "--v8-disable-maglev",
)
PUBLIC_FLAGS = ("-std=c++20", "-fno-rtti", "-DV8_PROMISE_INTERNAL_FIELD_COUNT=1")
GYP_INCLUDE = ROOT / "packages/v8/pedigree.gypi"
CLOCK_PATCH = ROOT / "packages/v8/monotonic-clock.diff"
CLOCK_SOURCE = "deps/v8/third_party/abseil-cpp/absl/base/internal/sysinfo.cc"
LINK_FLAGS = ("-ldl", "-static-libstdc++", "-static-libgcc", "-no-pie",
              "-Wl,-Ttext-segment=0x400000", "-Wl,-z,max-page-size=4096",
              "-Wl,-z,common-page-size=4096", "-Wl,-z,noexecstack",
              "-Wl,--dynamic-linker=/usr/lib/ld-musl-x86_64.so.1")
SERIAL_OBJECT = ("Release/obj.target/v8_compiler/deps/v8/src/compiler/"
                 "turboshaft/csa-optimize-phase.o")


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(pin, offline):
    path = ROOT / "downloads" / pin["url"].rsplit("/", 1)[1]
    if offline:
        if not path.is_file() or digest(path) != pin["sha256"]:
            raise RuntimeError("missing or invalid cached source: " + str(path))
    else:
        steps.download(pin["url"], str(path), sha256=pin["sha256"])
    return path


def prepare_source(cache, offline):
    archive = fetch(PINS["source"], offline)
    source = cache / "source"
    stamp = PINS["source"]["sha256"]
    marker = source / ".pedigree-source"
    if not marker.is_file() or marker.read_text().strip() != stamp:
        from support.build import _safe_members
        shutil.rmtree(source, ignore_errors=True)
        source.mkdir(parents=True)
        with tarfile.open(archive) as bundle:
            bundle.extractall(source, members=_safe_members(bundle), filter="data")
        marker.write_text(stamp + "\n")
    version_header = (source / "deps/v8/include/v8-version.h").read_text()
    version = ".".join(re.search(r"#define V8_" + name + r"\s+(\d+)",
                                 version_header).group(1)
                       for name in ("MAJOR_VERSION", "MINOR_VERSION",
                                    "BUILD_NUMBER", "PATCH_LEVEL"))
    if version != PINS["version"]:
        raise RuntimeError("source bundle contains unexpected V8 version: " + version)
    # Reapply this small overlay to pristine input, preserving unchanged object
    # timestamps and the rest of the expensive incremental compilation cache.
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        original = Path(temporary) / "sysinfo.cc"
        with tarfile.open(archive) as bundle:
            member = archive.name.removesuffix(".tar.xz") + "/" + CLOCK_SOURCE
            original.write_bytes(bundle.extractfile(member).read())
        subprocess.run(["patch", "--batch", "--fuzz=0", str(original),
                        str(CLOCK_PATCH)], check=True)
        patched = original.read_bytes()
        destination = source / CLOCK_SOURCE
        if destination.read_bytes() != patched:
            destination.write_bytes(patched)
    headers_archive = fetch(PINS["linux_headers"], offline)
    headers = cache / "linux-headers"
    header_marker = headers / ".sha256"
    if not header_marker.is_file() or header_marker.read_text().strip() != PINS["linux_headers"]["sha256"]:
        shutil.rmtree(headers, ignore_errors=True)
        headers.mkdir()
        with tarfile.open(headers_archive, ignore_zeros=True) as bundle:
            members = [m for m in bundle.getmembers() if m.isfile() and
                       m.name.startswith(("usr/include/linux/", "usr/include/asm/",
                                          "usr/include/asm-generic/"))]
            bundle.extractall(headers, members=members, filter="data")
        header_marker.write_text(PINS["linux_headers"]["sha256"] + "\n")
    return source, headers / "usr/include"


def build_environment(cache, headers):
    env = os.environ.copy()
    prefix = Path(env.get("PEDIGREE_TOOLCHAIN_ROOT", "/opt/pedigree"))
    for variable, tool in (("CC", "gcc"), ("CXX", "g++"), ("AR", "ar")):
        env[variable] = str(prefix / "bin" / ("x86_64-pedigree-" + tool))
        env[variable + "_host"] = "/usr/bin/" + tool
    env["LINK_host"] = env["CXX_host"]
    # Linux platform selection must not add host libc headers or affect the
    # native generators. The archive itself retains the SDK's C++ ABI.
    flags = shlex.join(["-O2", "-g0", "-fPIC", "-D__linux__=1",
                        "-U__pedigree__", "-U__PEDIGREE__",
                        "-isystem", str(headers)])
    env.update(CFLAGS=flags, CXXFLAGS=flags, CPPFLAGS="", LIBS="",
               CFLAGS_host="-O2 -g0", CXXFLAGS_host="-O2 -g0", CPPFLAGS_host="",
               LDFLAGS_host="", LDFLAGS="-Wl,-z,max-page-size=4096",
               GYP_DEFINES="", MAKEFLAGS="")
    return env


def install(source, cache, env):
    stage = cache / "root"
    shutil.rmtree(stage, ignore_errors=True)
    libdir = stage / "usr/lib"
    libdir.mkdir(parents=True)
    archives = [source / "out/Release/obj.target/tools/v8_gypfiles" /
                ("lib" + name + ".a") for name in ARCHIVES]
    for archive in archives:
        if not archive.is_file():
            raise RuntimeError("missing target V8 archive: " + str(archive))
    output = libdir / "libv8.a"
    # MRI ADDLIB materializes members of GYP's thin archives; a PUP must not
    # depend on object files remaining in the build tree.
    commands = ["CREATE " + str(output)] + ["ADDLIB " + str(a) for a in archives]
    subprocess.run([env["AR"], "-M"], input="\n".join(commands + ["SAVE", "END", ""]),
                   text=True, check=True)
    if output.open("rb").read(8) != b"!<arch>\n":
        raise RuntimeError("V8 archive was not materialized")
    subprocess.run([env["AR"], "sD", str(output)], check=True)
    shutil.copytree(source / "deps/v8/include", stage / "usr/include/v8")
    shutil.copytree(source / "out/Release/obj/gen/inspector-generated-output-root/include/inspector",
                    stage / "usr/include/v8/inspector")
    pc = libdir / "pkgconfig/v8.pc"
    pc.parent.mkdir()
    pc.write_text(
        "prefix=/usr\nlibdir=${prefix}/lib\nincludedir=${prefix}/include\n\n"
        "Name: V8\nDescription: V8 JavaScript embedding engine\n"
        "Version: " + PINS["version"] + "\n"
        "Libs: -L${libdir} -lv8\nLibs.private: -pthread -ldl\n"
        "Cflags: -I${includedir}/v8 " + " ".join(PUBLIC_FLAGS) + "\n")
    docs = stage / "usr/share/doc/v8"
    docs.mkdir(parents=True)
    shutil.copy2(source / "LICENSE", docs / "THIRD-PARTY-NOTICES")
    shutil.copy2(source / "deps/v8/LICENSE", docs / "LICENSE")
    shutil.copy2(ROOT / "packages/v8/README.md", docs / "README.md")
    shutil.copy2(CLOCK_PATCH, docs / CLOCK_PATCH.name)
    shutil.copy2(ROOT / "language-ports/v8/probe.cc", docs / "probe.cc")
    for name in ("GPL-3.0.txt", "GCC-Runtime-Library-Exception-3.1.txt"):
        shutil.copy2(ROOT / "packages/rust/licenses" / name, docs / name)
    shutil.copytree(ROOT / "packages/v8/licenses", docs / "licenses")
    bindir = stage / "usr/bin"
    bindir.mkdir()
    probe = bindir / "v8-qualify"
    subprocess.run(
        [env["CXX"], *PUBLIC_FLAGS, "-O2", "-g0", "-pthread",
         "-I" + str(stage / "usr/include/v8"), str(docs / "probe.cc"),
         str(output), *LINK_FLAGS, "-o", str(probe)],
        env=env, check=True)
    artifact = ROOT / ".build/language-ports/v8/v8-qualify"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(probe, artifact)
    (docs / "build.json").write_text(json.dumps({
        "version": PINS["version"], "source": PINS["source"],
        "linux_headers": PINS["linux_headers"],
        "configure": list(CONFIGURE), "archive_sha256": digest(output),
        "gyp_include_sha256": digest(GYP_INCLUDE), "abseil_waiter": "pthread",
        "clock_patch_sha256": digest(CLOCK_PATCH),
        "target_cxxflags": env["CXXFLAGS"], "serial_object": SERIAL_OBJECT,
        "consumer_cflags": list(PUBLIC_FLAGS),
        "probe_sha256": digest(probe),
        "compiler": subprocess.check_output([env["CXX"], "--version"], text=True).splitlines()[0],
        "runtime_sha256": {name: digest(subprocess.check_output(
            [env["CXX"], "-print-file-name=" + name], text=True).strip())
            for name in ("libstdc++.a", "libgcc.a")},
        "features": {"pointer_compression": False, "sandbox": False,
                     "intl": False, "inspector": True, "maglev": False, "sparkplug": True,
                     "turbofan": True, "webassembly": True},
    }, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / ".build/x86_64/v8")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--abseil-only", action="store_true",
                        help="build only Abseil and its small platform qualification probe")
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        parser.error("use the linux/amd64 ports Docker builder")
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    cache = args.cache.resolve()
    if any(c.isspace() for c in str(cache)):
        parser.error("the V8 build path cannot contain whitespace")
    cache.mkdir(parents=True, exist_ok=True)
    source, headers = prepare_source(cache, args.offline)
    env = build_environment(cache, headers)
    subprocess.run([sys.executable, "configure.py", *CONFIGURE,
                    "-I", str(GYP_INCLUDE)], cwd=source, env=env, check=True)
    make = ["make", "-C", "out", "BUILDTYPE=Release"]
    if args.abseil_only:
        subprocess.run([*make, "-j" + str(args.jobs), "abseil"],
                       cwd=source, env=env, check=True)
        probe = ROOT / ".build/language-ports/v8/abseil-qualify"
        probe.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            env["CXX"], *shlex.split(env["CXXFLAGS"]), "-std=c++20", "-fno-rtti",
            "-fno-exceptions", "-pthread", "-D_GLIBCXX_USE_CXX11_ABI=1",
            "-I" + str(source / "deps/v8/third_party/abseil-cpp"),
            str(ROOT / "language-ports/v8/abseil-probe.cc"),
            str(source / "out/Release/obj.target/tools/v8_gypfiles/libabseil.a"),
            *LINK_FLAGS, "-o", str(probe)], env=env, check=True)
        return
    bytecodes = source / "out/Release/obj/gen/generate-bytecode-output-root/builtins-generated/bytecodes-builtins-list.h"
    before = (bytecodes.read_bytes(), bytecodes.stat()) if bytecodes.is_file() else None
    subprocess.run([*make, "-j" + str(args.jobs), "v8_internal_headers",
                    "v8_pch", "v8_compiler_sources"], cwd=source, env=env, check=True)
    # This generator truncates its output even when only a linked library
    # changed. Preserve identical output so it does not rebuild the engine.
    if before and bytecodes.read_bytes() == before[0]:
        os.utime(bytecodes, ns=(before[1].st_atime_ns, before[1].st_mtime_ns))
    # Later make invocations must consume the prepared header even when its
    # unchanged contents have an older timestamp than the relinked generator.
    make += ["-o", str(bytecodes)]
    # GCC's reducer-template compilation exceeds an 8 GiB builder's memory
    # when it overlaps other large units. Keep its normal optimization level.
    subprocess.run([*make, "-j1", str(source / "out" / SERIAL_OBJECT)],
                   cwd=source, env=env, check=True)
    # GYP's static v8 umbrella does not build its dependency archives itself.
    subprocess.run([*make, "-j" + str(args.jobs),
                    *ARCHIVES], cwd=source, env=env, check=True)
    install(source, cache, env)


if __name__ == "__main__":
    main()
