import os
import tempfile
import unittest

from .package import GettextPackage


class GettextPackageTest(unittest.TestCase):
    def test_postdeploy_removes_unavailable_optional_tools(self):
        with tempfile.TemporaryDirectory() as deploydir:
            bindir = os.path.join(deploydir, "usr", "bin")
            fixture_dir = os.path.join(
                deploydir,
                "usr",
                "share",
                "doc",
                "gettext",
                "examples",
                "build-aux",
            )
            os.makedirs(bindir)
            os.makedirs(fixture_dir)

            spit = os.path.join(bindir, "spit")
            fixture = os.path.join(fixture_dir, "csharpexec-test.exe")
            retained = os.path.join(bindir, "gettext")
            for path in (spit, fixture, retained):
                with open(path, "w", encoding="utf-8") as artifact:
                    artifact.write("fixture\n")

            GettextPackage(__file__).postdeploy({}, "", deploydir)

            self.assertFalse(os.path.exists(spit))
            self.assertFalse(os.path.exists(fixture))
            self.assertTrue(os.path.exists(retained))


if __name__ == "__main__":
    unittest.main()
