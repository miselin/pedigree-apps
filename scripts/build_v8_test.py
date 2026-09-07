import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "build_v8", Path(__file__).with_name("build-v8.py"))
v8 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(v8)


class V8BuildTest(unittest.TestCase):
    def test_offline_build_rejects_corrupt_cached_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "downloads").mkdir()
            archive = root / "downloads/source.tar.xz"
            archive.write_bytes(b"incomplete download")
            pin = {"url": "https://example.invalid/source.tar.xz",
                   "sha256": hashlib.sha256(b"verified source").hexdigest()}
            with mock.patch.object(v8, "ROOT", root), \
                    mock.patch.object(v8.steps, "download") as download:
                with self.assertRaisesRegex(RuntimeError, "invalid cached source"):
                    v8.fetch(pin, offline=True)
                archive.write_bytes(b"verified source")
                self.assertEqual(v8.fetch(pin, offline=True), archive)
                download.assert_not_called()

    def test_target_flags_cannot_contaminate_host_generators(self):
        inherited = {
            "PEDIGREE_TOOLCHAIN_ROOT": "/sdk",
            "CFLAGS": "-D__PEDIGREE__ --sysroot=/target",
            "CXXFLAGS_host": "--sysroot=/target",
            "CPPFLAGS_host": "-I/target/include",
            "LDFLAGS_host": "-L/target/lib",
            "GYP_DEFINES": "v8_enable_pointer_compression=1",
        }
        with mock.patch.dict(v8.os.environ, inherited, clear=True):
            env = v8.build_environment(Path("/cache"), Path("/uapi"))
        for key in ("CFLAGS_host", "CXXFLAGS_host", "CPPFLAGS_host", "LDFLAGS_host"):
            self.assertNotIn("/target", env[key])
            self.assertNotIn("PEDIGREE", env[key])
        self.assertEqual(env["GYP_DEFINES"], "")
        self.assertNotEqual(env["CXX"], env["CXX_host"])


if __name__ == "__main__":
    unittest.main()
