import hashlib
import json
import os
from pathlib import Path
import shutil
import stat

from support import buildsystem


SOURCE_REVISION = "694b6319d3ad2399f6e435760a22d9b9357f0697"
VERSION = "0.0.0.20260907"
COMPONENTS = (("codex-cli", "codex"),
              ("codex-code-mode-host", "codex-code-mode-host"))
EXPERIMENTAL_REASON = "Full CLI tool workflows, interactive terminal sessions, authenticated networking, and OS sandbox enforcement remain unqualified."


def _digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def _merge_tree(source, destination):
    destination.mkdir(parents=True, exist_ok=True)
    for entry in sorted(source.iterdir()):
        target = destination / entry.name
        details = entry.lstat()
        mode = stat.S_IMODE(details.st_mode)
        if os.path.lexists(target):
            existing = target.lstat()
            same_mode = mode == stat.S_IMODE(existing.st_mode)
            if same_mode and stat.S_ISDIR(details.st_mode) and stat.S_ISDIR(existing.st_mode):
                _merge_tree(entry, target)
                continue
            if same_mode and stat.S_ISREG(details.st_mode) and stat.S_ISREG(existing.st_mode):
                if _digest(entry) == _digest(target):
                    continue
            if same_mode and stat.S_ISLNK(details.st_mode) and stat.S_ISLNK(existing.st_mode):
                if os.readlink(entry) == os.readlink(target):
                    continue
            raise RuntimeError("Codex component payload collision: %s" % target)
        if stat.S_ISDIR(details.st_mode):
            _merge_tree(entry, target)
            target.chmod(mode)
        elif stat.S_ISREG(details.st_mode):
            shutil.copy2(entry, target)
        elif stat.S_ISLNK(details.st_mode):
            target.symlink_to(os.readlink(entry))
        else:
            raise RuntimeError("unsupported Codex component payload: %s" % entry)


class CodexPackage(buildsystem.Package):
    def name(self):
        return "codex"

    def version(self):
        return VERSION

    def build_requires(self):
        return [name for name, _ in COMPONENTS]

    def install_deps(self):
        return ["ca-certificates"]

    def deploy(self, env, srcdir, deploydir):
        destination = Path(deploydir)
        components = []
        roots = []
        for name, executable in COMPONENTS:
            base = Path(env["OUTPUT_BASE"]) / name / VERSION
            root = base / "root"
            marker = base / ".complete"
            if (not root.is_dir() or root.is_symlink() or not marker.is_file()
                    or marker.read_text() != "%s-%s\n" % (name, VERSION)):
                raise RuntimeError("Codex component build is incomplete: %s" % name)
            receipt_path = Path("usr/share/doc") / name / "build.json"
            receipt = json.loads((root / receipt_path).read_text())
            binary_path = Path("usr/libexec") / executable
            binary = root / binary_path
            if (not binary.is_file() or binary.is_symlink()
                    or not stat.S_IMODE(binary.stat().st_mode) & 0o111):
                raise RuntimeError("missing executable Codex component: %s" % binary_path)
            binary_digest = _digest(binary)
            if (receipt.get("revision") != SOURCE_REVISION
                    or receipt.get("binary_sha256") != binary_digest):
                raise RuntimeError("Codex component provenance mismatch: %s" % name)
            components.append({
                "name": name,
                "version": VERSION,
                "binary": "/" + str(binary_path),
                "binary_sha256": binary_digest,
                "provenance": "/" + str(receipt_path),
                "provenance_sha256": _digest(root / receipt_path),
            })
            roots.append(root)

        for root in roots:
            _merge_tree(root, destination)

        # The CLI already embeds App Server; its large standalone binary is
        # unnecessary. The Code Mode host stays beside the actual CLI binary,
        # where upstream sibling discovery expects to find it.
        launcher = destination / "usr/bin/codex-app-server"
        if os.path.lexists(launcher) or os.path.lexists(destination / "usr/libexec/codex-app-server"):
            raise RuntimeError("standalone App Server payload conflicts with unified Codex")
        launcher.write_text('#!/bin/sh\nexec /usr/libexec/codex app-server "$@"\n')
        launcher.chmod(0o755)

        docs = destination / "usr/share/doc/codex"
        if os.path.lexists(docs):
            raise RuntimeError("Codex component collides with unified documentation")
        docs.mkdir(parents=True)
        shutil.copy2(Path(self._path) / "README.md", docs / "README.md")
        provenance = {
            "revision": SOURCE_REVISION,
            "version": VERSION,
            "components": components,
            "code_mode_host": True,
            "recipe_sha256": _digest(Path(self._path) / "package.py"),
            "app_server_launcher_sha256": _digest(launcher),
        }
        (docs / "build.json").write_text(json.dumps(provenance, indent=2) + "\n")
