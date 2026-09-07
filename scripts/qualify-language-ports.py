#!/usr/bin/env python3
"""Inject a language-port suite into a disposable ext2 disk and qualify in QEMU.

Suite paths are relative to the JSON file. `files` entries name a source,
absolute guest destination, and optional octal mode. `trees` entries recursively
install a source directory. Each `cases` entry has a unique name, a shell command,
and exact output lines in `markers`. See language-ports for the language probes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time


PREFIX = "LANGUAGE-PORTS"
HOOK = "/etc/init.d/05_contracts.sh"
ANSI = re.compile(r"(?:\x1b\[|\x9b)[0-?]*[ -/]*[@-~]")
KERNEL_LOG = re.compile(r"\((?:NN|WW|EE|FF)\) \[[^\]\r\n]+\][^\r\n]*\r?\n")
FATAL = re.compile(r"\(FF\)|\| KERNEL MODE \||PANIC:|FATAL:|fatal error:|Page Fault Exception|Double Fault Exception|Triple fault")


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def quote_debugfs(value: str | Path) -> str:
    value = str(value)
    if any(c in value for c in '\r\n\0"\\'):
        raise ValueError(f"unsupported debugfs path: {value!r}")
    return '"' + value + '"'


def guest_path(value: str, allow_root: bool = False) -> str:
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts or (str(path) == "/" and not allow_root):
        raise ValueError(f"guest destination must be an absolute file/directory: {value}")
    quote_debugfs(value)
    return str(path)


def load_suite(path: Path) -> dict:
    suite = json.loads(path.read_text())
    cases = suite.get("cases", [])
    names = set()
    if not cases:
        raise ValueError("suite needs at least one case")
    for case in cases:
        name = case["name"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", name) or name in names:
            raise ValueError(f"invalid or duplicate case name: {name}")
        names.add(name)
        if not isinstance(case["command"], str) or not case["command"].strip():
            raise ValueError(f"case {name} requires a shell command")
        if not case.get("markers") or any(
            not isinstance(marker, str) or not marker or "\n" in marker or "\r" in marker
            for marker in case["markers"]
        ):
            raise ValueError(f"case {name} requires exact nonempty marker lines")
    for kind in ("files", "trees"):
        for item in suite.get(kind, []):
            item["source"] = str((path.parent / item["source"]).absolute())
            item["destination"] = guest_path(item["destination"], allow_root=kind == "trees")
            source = Path(item["source"])
            if kind == "trees" and (source.is_symlink() or not source.is_dir()):
                raise ValueError(f"tree source is not a directory: {source}")
            if kind == "files" and not (source.is_file() or source.is_symlink()):
                raise ValueError(f"file source is unavailable: {source}")
    return suite


def boot_script(cases: list[dict]) -> str:
    lines = ["#!/bin/sh", "exec >/dev/ttyS0 2>&1", f"echo '{PREFIX}: BEGIN'"]
    for case in cases:
        name = case["name"]
        lines += [
            f"echo '{PREFIX}: begin {name}'",
            # A child shell makes command-local exit and shell options harmless
            # to the enclosing status protocol.
            f"/bin/sh -c {shlex.quote(case['command'])}",
            "result=$?",
            f'echo "{PREFIX}: status {name} $result"',
            '[ "$result" -eq 0 ] || exit "$result"',
        ]
    lines += [f"echo '{PREFIX}: END PASS'", ""]
    return "\n".join(lines)


def evaluate_output(output: str, cases: list[dict]) -> tuple[str, str]:
    clean = ANSI.sub("", output).replace("\0", "")
    fatal = FATAL.search(clean)
    if fatal:
        return "fail", f"terminal failure: {fatal.group()}"
    # Kernel logging can interrupt a userspace line on their shared serial port.
    clean = KERNEL_LOG.sub("", clean.replace("\r", ""))
    clean = clean[: clean.rfind("\n") + 1]
    lines = clean.splitlines()
    expected = [case["name"] for case in cases]
    statuses = re.findall(rf"^{PREFIX}: status ([a-z0-9_-]+) (-?\d+)$", clean, re.M)
    for name, status_code in statuses:
        if name not in expected or int(status_code) != 0:
            return "fail", f"case {name} exited {status_code}"
    if [name for name, _ in statuses] != expected[: len(statuses)]:
        return "fail", "duplicate or out-of-order case status"
    if f"{PREFIX}: END PASS" not in lines:
        return "pending", "waiting for suite end marker"
    if lines.count(f"{PREFIX}: BEGIN") != 1 or lines.count(f"{PREFIX}: END PASS") != 1:
        return "fail", "missing or duplicate suite boundaries"
    if [name for name, _ in statuses] != expected:
        return "fail", "suite ended without every case status"
    cursor = lines.index(f"{PREFIX}: BEGIN") + 1
    for case in cases:
        begin = f"{PREFIX}: begin {case['name']}"
        status_line = f"{PREFIX}: status {case['name']} 0"
        try:
            start = lines.index(begin, cursor)
            end = lines.index(status_line, start + 1)
        except ValueError:
            return "fail", f"missing boundaries for {case['name']}"
        missing = [marker for marker in case["markers"] if marker not in lines[start + 1 : end]]
        if missing:
            return "fail", f"case {case['name']} missing markers: {missing}"
        cursor = end + 1
    if lines.index(f"{PREFIX}: END PASS") < cursor:
        return "fail", "suite end precedes case results"
    return "pass", "all case statuses and markers verified"


def clone_image(source: Path, destination: Path) -> None:
    if destination.exists():
        raise ValueError(f"refusing to replace artifact: {destination}")
    if sys.platform == "darwin":
        copied = subprocess.run(["/bin/cp", "-c", str(source), str(destination)], capture_output=True)
        if copied.returncode == 0:
            return
        destination.unlink(missing_ok=True)
    shutil.copyfile(source, destination)


def grow_disk(disk: Path, size_mib: int, e2fsck: str, resize2fs: str, out: Path) -> None:
    size = size_mib * 1024 * 1024
    if size < disk.stat().st_size:
        raise ValueError("disk size would shrink the cloned image")
    if size == disk.stat().st_size:
        return
    with (out / "resize.log").open("w") as log:
        checked = subprocess.run([e2fsck, "-f", "-p", str(disk)], stdout=log, stderr=log)
        if checked.returncode not in (0, 1):
            raise ValueError(f"pre-resize e2fsck failed with status {checked.returncode}")
        with disk.open("r+b") as image:
            image.truncate(size)
        subprocess.run([resize2fs, str(disk)], stdout=log, stderr=log, check=True)
        checked = subprocess.run([e2fsck, "-f", "-p", str(disk)], stdout=log, stderr=log)
        if checked.returncode not in (0, 1):
            raise ValueError(f"post-resize e2fsck failed with status {checked.returncode}")


def inject_suite(debugfs: str, disk: Path, suite: dict, out: Path) -> list[dict]:
    hook = out / "05_contracts.sh"
    hook.write_text(boot_script(suite["cases"]))
    files = list(suite.get("files", [])) + [{"source": str(hook), "destination": HOOK, "mode": "0755"}]
    directories = set()
    for tree in suite.get("trees", []):
        root = Path(tree["source"])
        directories.add(tree["destination"])
        for source in sorted(root.rglob("*")):
            destination = str(PurePosixPath(tree["destination"]) / source.relative_to(root).as_posix())
            if source.is_dir() and not source.is_symlink():
                directories.add(destination)
            else:
                files.append({"source": str(source), "destination": destination})
    destinations = [item["destination"] for item in files]
    if len(set(destinations)) != len(destinations):
        raise ValueError("suite contains overlapping file destinations")
    for destination in destinations + list(directories):
        directories.update(str(parent) for parent in PurePosixPath(destination).parents if str(parent) != "/")
    directories.discard("/")
    commands = [f"mkdir {quote_debugfs(directory)}" for directory in sorted(directories, key=lambda x: (x.count('/'), x))]
    identities = []
    for item in files:
        source, destination = Path(item["source"]), guest_path(item["destination"])
        target = quote_debugfs(destination)
        commands.append(f"rm {target}")
        identity = {"source": str(source), "destination": destination}
        if source.is_symlink():
            link = os.readlink(source)
            commands.append(f"symlink {target} {quote_debugfs(link)}")
            identity["link"] = link
        else:
            if not source.is_file():
                raise ValueError(f"unsupported source type: {source}")
            mode = int(str(item.get("mode", oct(stat.S_IMODE(source.stat().st_mode)))), 8)
            if mode & ~0o777:
                raise ValueError(f"only permission bits are supported: {source}")
            commands += [f"write {quote_debugfs(source)} {target}", f"set_inode_field {target} mode 0{stat.S_IFREG | mode:o}"]
            identity.update(sha256=digest(source), mode=oct(mode))
        identities.append(identity)
    command_file = out / "inject.debugfs"
    command_file.write_text("\n".join(commands) + "\n")
    with (out / "inject.log").open("w") as log:
        subprocess.run([debugfs, "-w", "-f", str(command_file), str(disk)], stdout=log, stderr=log, check=True)
    # debugfs returns zero even when an individual write fails. Read every payload
    # back before booting so a full disk cannot qualify an older installed binary.
    with tempfile.TemporaryDirectory(prefix="verify-", dir=out) as temporary:
        verify = Path(temporary)
        dump_commands = [f"dump {quote_debugfs(item['destination'])} {quote_debugfs(verify / str(index))}"
                         for index, item in enumerate(identities) if "sha256" in item]
        command_file = out / "verify.debugfs"
        command_file.write_text("\n".join(dump_commands) + "\n")
        with (out / "verify.log").open("w") as log:
            subprocess.run([debugfs, "-f", str(command_file), str(disk)], stdout=log, stderr=log, check=True)
        for index, item in enumerate(identities):
            if "sha256" in item:
                copy = verify / str(index)
                if not copy.is_file() or digest(copy) != item["sha256"]:
                    raise ValueError(f"injected content differs: {item['destination']}")
            else:
                result = subprocess.check_output([debugfs, "-R", f"stat {quote_debugfs(item['destination'])}", str(disk)], stderr=subprocess.DEVNULL, text=True)
                if f'Fast link dest: "{item["link"]}"' not in result:
                    raise ValueError(f"could not verify injected symlink: {item['destination']}")
    return identities


def qemu_command(args: argparse.Namespace, out: Path) -> list[str]:
    return [
        args.qemu, "-machine", "pc", "-cpu", args.cpu,
        "-drive", f"file={out / 'disk.img'},if=ide,index=0,format=raw",
        "-drive", f"file={out / 'boot.iso'},if=ide,index=2,format=raw,media=cdrom,readonly=on",
        "-boot", "order=d,strict=on", "-vga", "cirrus", "-display", "none",
        "-monitor", "none", "-serial", f"file:{out / 'serial.log'}",
        "-m", str(args.memory), "-smp", str(args.cpus), "-snapshot",
        "-nic", "none", "-no-reboot", "-no-shutdown",
    ]


def run_guest(command: list[str], out: Path, cases: list[dict], timeout: float) -> dict:
    started = time.monotonic()
    state, reason = "fail", "QEMU exited before suite completion"
    with (out / "qemu.log").open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        try:
            while True:
                serial = out / "serial.log"
                output = serial.read_text(errors="replace") if serial.exists() else ""
                state, reason = evaluate_output(output, cases)
                if state != "pending":
                    if state == "fail":
                        # Runtime failures print their stack after the fatal line.
                        # Retain that tail without reconsidering the failed result.
                        try:
                            process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            pass
                    break
                if process.poll() is not None:
                    state, reason = "fail", f"QEMU exited {process.returncode} before suite completion"
                    break
                if time.monotonic() - started >= timeout:
                    state, reason = "fail", f"timeout after {timeout:g} seconds: {reason}"
                    break
                time.sleep(0.1)
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
    return {"status": state, "reason": reason, "elapsed_seconds": round(time.monotonic() - started, 2), "qemu_exit_status": process.returncode}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso", type=Path, required=True, help="fresh Pedigree boot ISO")
    parser.add_argument("--disk", type=Path, required=True, help="raw ext2 Pedigree system disk")
    parser.add_argument("--disk-size-mib", type=int, help="grow the cloned ext2 disk to this size; never shrink")
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="new directory for retained images and logs")
    parser.add_argument("--cpus", type=int, choices=(1, 4), default=1)
    parser.add_argument("--memory", type=int, default=2048, help="guest RAM in MiB")
    parser.add_argument("--cpu", default="max", help="QEMU CPU model; max supplies hardware entropy")
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--qemu", default="qemu-system-x86_64")
    parser.add_argument("--debugfs", default=shutil.which("debugfs") or "/opt/homebrew/opt/e2fsprogs/sbin/debugfs")
    parser.add_argument("--e2fsck", default=shutil.which("e2fsck") or "/opt/homebrew/opt/e2fsprogs/sbin/e2fsck")
    parser.add_argument("--resize2fs", default=shutil.which("resize2fs") or "/opt/homebrew/opt/e2fsprogs/sbin/resize2fs")
    parser.add_argument("--prepare-only", action="store_true", help="prepare and verify images without booting")
    args = parser.parse_args()
    out = args.output_dir.resolve()
    created = False
    try:
        if args.timeout <= 0 or args.memory <= 0:
            raise ValueError("timeout and memory must be positive")
        suite = load_suite(args.suite.resolve())
        for path in (args.iso, args.disk):
            if not path.is_file():
                raise ValueError(f"image unavailable: {path}")
        if any(c in str(out) for c in ',\r\n\0'):
            raise ValueError("output directory cannot contain commas or control characters")
        out.mkdir(parents=True, exist_ok=False)
        created = True
        clone_image(args.iso.resolve(), out / "boot.iso")
        clone_image(args.disk.resolve(), out / "disk.img")
        metadata = {
            "suite": suite, "source_iso": str(args.iso.resolve()), "source_disk": str(args.disk.resolve()),
            "iso_sha256": digest(out / "boot.iso"), "source_disk_sha256": digest(out / "disk.img"),
            "source_disk_bytes": (out / "disk.img").stat().st_size,
            "cpus": args.cpus, "memory_mib": args.memory,
            "qualification_scope": "guest execution in one boot; no persistence claim",
        }
        if args.disk_size_mib is not None:
            grow_disk(out / "disk.img", args.disk_size_mib, args.e2fsck, args.resize2fs, out)
        metadata["disk_bytes"] = (out / "disk.img").stat().st_size
        metadata["payload"] = inject_suite(args.debugfs, out / "disk.img", suite, out)
        metadata["injected_disk_sha256"] = digest(out / "disk.img")
        command = qemu_command(args, out)
        metadata["qemu_command"] = command
        (out / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(f"QEMU command: {shlex.join(command)}", flush=True)
        print(f"Artifacts: {out}", flush=True)
        result = {"status": "prepared"} if args.prepare_only else run_guest(command, out, suite["cases"], args.timeout)
        (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        return 0 if result["status"] in ("pass", "prepared") else 1
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"Qualification failed: {error}", file=sys.stderr)
        if created:
            (out / "error.txt").write_text(str(error) + "\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
