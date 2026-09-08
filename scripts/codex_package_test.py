import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest

from packages.codex.package import COMPONENTS, SOURCE_REVISION, VERSION, CodexPackage


RECIPE = Path(__file__).resolve().parents[1] / "packages/codex/package.py"


class CodexPackageTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="codex-package-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.output = self.base / "components"
        self.stage = self.base / "unified"
        self.package = CodexPackage(str(RECIPE))
        self.roots = {}
        for name, executable in COMPONENTS:
            base = self.output / name / VERSION
            root = base / "root"
            self.roots[name] = root
            binary = self.write(root / "usr/libexec" / executable,
                                b"\x7fELFfixture-" + name.encode(), 0o755)
            self.write(root / "usr/bin" / executable,
                       ('#!/bin/sh\nexec /usr/libexec/%s "$@"\n' % executable).encode(), 0o755)
            self.write(root / "usr/share" / name / "defaults.toml", b"upstream = true\n", 0o644)
            receipt = {"revision": SOURCE_REVISION,
                       "binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                       "component_detail": name}
            self.write(root / "usr/share/doc" / name / "build.json",
                       (json.dumps(receipt) + "\n").encode(), 0o644)
            self.write(root / "usr/share/doc" / name / "LICENSE", b"component notice\n", 0o644)
            self.write(base / ".complete", (name + "-" + VERSION + "\n").encode(), 0o644)

    @staticmethod
    def write(path, contents, mode=0o644):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents)
        path.chmod(mode)
        return path

    def deploy(self):
        self.package.deploy({"OUTPUT_BASE": str(self.output)}, "", str(self.stage))

    def test_bundle_preserves_components_and_discovers_sibling_host(self):
        left, right = self.roots.values()
        for root in (left, right):
            self.write(root / "usr/share/common.txt", b"identical shared payload\n")
        (left / "usr/bin/codex-alias").symlink_to("codex")
        self.deploy()
        self.assertEqual(self.package.build_requires(), [name for name, _ in COMPONENTS])
        self.assertEqual(self.package.install_deps(), ["ca-certificates"])
        binary_directory = self.stage / "usr/libexec"
        self.assertEqual({path.name for path in binary_directory.iterdir()},
                         {"codex", "codex-code-mode-host"})
        self.assertEqual((self.stage / "usr/bin/codex-alias").readlink(), Path("codex"))
        launcher = self.stage / "usr/bin/codex-app-server"
        self.assertEqual(launcher.read_text(),
                         '#!/bin/sh\nexec /usr/libexec/codex app-server "$@"\n')
        self.assertEqual(stat.S_IMODE(launcher.stat().st_mode), 0o755)
        manifest = json.loads((self.stage / "usr/share/doc/codex/build.json").read_text())
        for component in manifest["components"]:
            root = self.roots[component["name"]]
            for relative in (component["binary"], component["provenance"]):
                original, merged = root / relative[1:], self.stage / relative[1:]
                self.assertEqual(merged.read_bytes(), original.read_bytes())
                self.assertEqual(stat.S_IMODE(merged.stat().st_mode),
                                 stat.S_IMODE(original.stat().st_mode))
            for filename in ("defaults.toml",):
                relative = Path("usr/share") / component["name"] / filename
                self.assertEqual((self.stage / relative).read_bytes(), (root / relative).read_bytes())
            receipt = self.stage / component["provenance"][1:]
            self.assertEqual(component["provenance_sha256"],
                             hashlib.sha256(receipt.read_bytes()).hexdigest())
            notice = Path("usr/share/doc") / component["name"] / "LICENSE"
            self.assertEqual((self.stage / notice).read_bytes(), (root / notice).read_bytes())
        self.assertFalse((self.stage / "etc").exists())

    def test_conflicting_contents_modes_types_and_links_are_rejected(self):
        left, right = self.roots.values()
        for conflict in ("contents", "mode", "type", "symlink"):
            with self.subTest(conflict=conflict), tempfile.TemporaryDirectory() as stage:
                self.stage = Path(stage)
                path = Path("usr/share") / conflict
                self.write(left / path, b"left")
                if conflict == "contents":
                    self.write(right / path, b"right")
                elif conflict == "mode":
                    self.write(right / path, b"left", 0o600)
                elif conflict == "type":
                    (right / path).mkdir()
                else:
                    (right / path).symlink_to("contents")
                with self.assertRaisesRegex(RuntimeError, "payload collision"):
                    self.deploy()
                (left / path).unlink()
                if conflict == "type":
                    (right / path).rmdir()
                else:
                    (right / path).unlink()

    def test_changed_binary_or_revision_cannot_reuse_provenance(self):
        root = self.roots["codex-code-mode-host"]
        receipt = root / "usr/share/doc/codex-code-mode-host/build.json"
        original = receipt.read_bytes()
        for field, value in (("revision", "another-revision"), ("binary_sha256", "0" * 64)):
            with self.subTest(field=field):
                record = json.loads(original)
                record[field] = value
                receipt.write_text(json.dumps(record))
                with self.assertRaisesRegex(RuntimeError, "provenance mismatch"):
                    self.deploy()
                self.assertFalse(self.stage.exists())
        receipt.write_bytes(original)

    def test_incomplete_component_is_rejected(self):
        (self.roots["codex-code-mode-host"].parent / ".complete").unlink()
        with self.assertRaisesRegex(RuntimeError, "component build is incomplete"):
            self.deploy()
        self.assertFalse(self.stage.exists())

    def test_host_must_be_executable_beside_cli(self):
        root = self.roots["codex-code-mode-host"]
        binary = root / "usr/libexec/codex-code-mode-host"
        binary.rename(root / "usr/bin/host-in-wrong-directory")
        with self.assertRaisesRegex(RuntimeError, "missing executable Codex component"):
            self.deploy()
        self.assertFalse(self.stage.exists())

    def test_standalone_app_server_payload_is_rejected(self):
        self.write(self.roots["codex-cli"] / "usr/libexec/codex-app-server", b"duplicate binary")
        with self.assertRaisesRegex(RuntimeError, "standalone App Server payload"):
            self.deploy()


if __name__ == "__main__":
    unittest.main()
