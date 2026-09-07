import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "qualify_language_ports", Path(__file__).with_name("qualify-language-ports.py")
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)

CASES = [{"name": "probe", "command": "echo PROBE-PASS", "markers": ["PROBE-PASS"]}]
PASS = """LANGUAGE-PORTS: BEGIN
LANGUAGE-PORTS: begin probe
PROBE-PASS
LANGUAGE-PORTS: status probe 0
LANGUAGE-PORTS: END PASS
"""


class SerialProtocolTest(unittest.TestCase):
    def test_requires_status_marker_and_ordered_boundaries(self):
        self.assertEqual(runner.evaluate_output(PASS, CASES)[0], "pass")
        for broken in (
            PASS.replace("status probe 0", "status probe 1"),
            PASS.replace("status probe 0", "status unknown 0"),
            PASS.replace("LANGUAGE-PORTS: status probe 0\n", ""),
            PASS.replace("PROBE-PASS\n", "prefix PROBE-PASS suffix\n"),
            "PROBE-PASS\n" + PASS.replace("PROBE-PASS\n", ""),
            PASS.replace("LANGUAGE-PORTS: BEGIN\n", ""),
            PASS.replace("LANGUAGE-PORTS: begin probe\n", ""),
            PASS + "LANGUAGE-PORTS: status probe 0\n",
            PASS + "(FF) kernel halted\n",
        ):
            with self.subTest(output=broken):
                self.assertEqual(runner.evaluate_output(broken, CASES)[0], "fail")

    def test_partial_end_line_is_not_completion(self):
        self.assertEqual(runner.evaluate_output(PASS.rstrip(), CASES)[0], "pending")

    def test_kernel_log_interleaving_and_terminal_escapes(self):
        output = PASS.replace("PROBE-PASS", "PROBE-(NN) [42.0] kernel diagnostic\r\nPASS")
        output = "\x1b[32m" + output.replace("\n", "\r\n") + "\x1b[0m"
        self.assertEqual(runner.evaluate_output(output, CASES)[0], "pass")

    def test_shell_failure_is_reported_even_for_explicit_exit(self):
        text = runner.boot_script([{**CASES[0], "command": "exit 17"}])
        text = text.replace("exec >/dev/ttyS0 2>&1\n", "")
        result = subprocess.run(["/bin/sh", "-c", text], capture_output=True, text=True)
        self.assertEqual(result.returncode, 17)
        self.assertIn("LANGUAGE-PORTS: status probe 17", result.stdout)
        self.assertNotIn("END PASS", result.stdout)

    def test_process_exit_and_timeout_are_failures(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            result = runner.run_guest([sys.executable, "-c", "pass"], out, CASES, 5)
            self.assertEqual(result["status"], "fail")
            self.assertIn("QEMU exited", result["reason"])
            result = runner.run_guest([sys.executable, "-c", "import time; time.sleep(30)"], out, CASES, 0.1)
            self.assertEqual(result["status"], "fail")
            self.assertIn("timeout", result["reason"])

    def test_failure_drain_retains_stack_and_never_changes_failure_to_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            script = (
                "import pathlib, time\n"
                f"serial = pathlib.Path({str(out / 'serial.log')!r})\n"
                "serial.write_text('fatal error: test failure\\n')\n"
                "time.sleep(0.25)\n"
                f"serial.write_text('diagnostic stack follows\\n' + {PASS!r})\n"
            )
            result = runner.run_guest([sys.executable, "-c", script], out, CASES, 5)
            self.assertEqual(result["status"], "fail")
            self.assertEqual(result["reason"], "terminal failure: fatal error:")
            self.assertIn("diagnostic stack follows", (out / "serial.log").read_text())
            self.assertEqual(result["qemu_exit_status"], 0)


class SuiteTest(unittest.TestCase):
    def test_resolves_sources_relative_to_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            (out / "probe").write_text("data")
            suite_path = out / "suite.json"
            suite_path.write_text(json.dumps({"files": [{"source": "probe", "destination": "/usr/bin/probe"}], "cases": CASES}))
            self.assertEqual(runner.load_suite(suite_path)["files"][0]["source"], str(out / "probe"))

    def test_rejects_ambiguous_guest_and_debugfs_paths(self):
        for path in ("relative", "/usr/../etc/file", "/", '/usr/bin/"probe'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                runner.guest_path(path)

    def test_root_destination_is_supported_only_for_trees(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            suite_path = out / "suite.json"
            suite_path.write_text(json.dumps({"trees": [{"source": ".", "destination": "/"}], "cases": CASES}))
            self.assertEqual(runner.load_suite(suite_path)["trees"][0]["destination"], "/")
            suite_path.write_text(json.dumps({"files": [{"source": "suite.json", "destination": "/"}], "cases": CASES}))
            with self.assertRaises(ValueError):
                runner.load_suite(suite_path)


class Ext2InjectionTest(unittest.TestCase):
    def test_prepares_verified_payload_without_modifying_source_disk(self):
        debugfs = shutil.which("debugfs") or "/opt/homebrew/opt/e2fsprogs/sbin/debugfs"
        mke2fs = shutil.which("mke2fs") or "/opt/homebrew/opt/e2fsprogs/sbin/mke2fs"
        e2fsck = shutil.which("e2fsck") or "/opt/homebrew/opt/e2fsprogs/sbin/e2fsck"
        resize2fs = shutil.which("resize2fs") or "/opt/homebrew/opt/e2fsprogs/sbin/resize2fs"
        if not all(Path(tool).exists() for tool in (debugfs, mke2fs, e2fsck, resize2fs)):
            self.skipTest("e2fsprogs unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "original.img"
            with original.open("wb") as stream:
                stream.truncate(16 * 1024 * 1024)
            subprocess.run([mke2fs, "-q", "-t", "ext2", "-F", str(original)], check=True, capture_output=True)
            original_digest = runner.digest(original)
            out = root / "artifacts"
            out.mkdir()
            disk = out / "disk.img"
            runner.clone_image(original, disk)
            runner.grow_disk(disk, 32, e2fsck, resize2fs, out)
            self.assertEqual(disk.stat().st_size, 32 * 1024 * 1024)
            with self.assertRaises(ValueError):
                runner.grow_disk(disk, 16, e2fsck, resize2fs, out)
            self.assertEqual(disk.stat().st_size, 32 * 1024 * 1024)
            tree = root / "payload with spaces"
            payload = tree / "usr/language"
            payload.mkdir(parents=True)
            (payload / "probe").write_bytes(bytes(range(256)))
            (payload / "probe").chmod(0o755)
            (payload / "alias").symlink_to("probe")
            suite = {"trees": [{"source": str(tree), "destination": "/"}], "cases": CASES}
            identities = runner.inject_suite(debugfs, disk, suite, out)
            self.assertEqual(len(identities), 3)
            self.assertNotIn('mkdir "/"\n', (out / "inject.debugfs").read_text())
            self.assertEqual(runner.digest(original), original_digest)
            status = subprocess.check_output([debugfs, "-R", "stat /usr/language/probe", str(disk)], stderr=subprocess.DEVNULL, text=True)
            self.assertIn("Mode:  0755", status)
            installed = subprocess.check_output([debugfs, "-R", f"cat {runner.HOOK}", str(disk)], stderr=subprocess.DEVNULL, text=True)
            self.assertEqual(installed, runner.boot_script(CASES))


if __name__ == "__main__":
    unittest.main()
