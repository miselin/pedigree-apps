import os
import tempfile
import unittest
from unittest import mock

from .package import MandocPackage


class MandocPackageTest(unittest.TestCase):

    def setUp(self):
        self.package = MandocPackage(__file__)
        self.env = {
            "CROSS_AR": "/opt/pedigree/bin/x86_64-pedigree-ar",
            "CROSS_CC": "/opt/pedigree/bin/x86_64-pedigree-gcc",
            "CFLAGS": "-O2 -D__PEDIGREE__",
            "CPPFLAGS": "-I/staged/usr/include",
            "LDFLAGS": "-Wl,-z,max-page-size=4096",
        }

    def test_runtime_contract_uses_formatter_aliases_without_man_conflict(self):
        self.assertEqual(self.package.build_requires(), ["zlib"])
        self.assertEqual(self.package.install_deps(), ["less", "zlib"])

        with tempfile.TemporaryDirectory() as srcdir:
            self.package.prebuild(self.env, srcdir)
            with open(
                os.path.join(srcdir, "configure.local"), encoding="utf-8"
            ) as config:
                contents = config.read()

        self.assertIn("PREFIX=/usr\n", contents)
        self.assertIn("MANDIR=/usr/share/man\n", contents)
        self.assertIn("BINM_MAN=mandoc-man\n", contents)
        self.assertIn("BINM_MAKEWHATIS=mandocdb\n", contents)
        self.assertNotIn("BINM_MAN=man\n", contents)

    def test_prebuild_supplies_all_cross_probe_answers(self):
        with tempfile.TemporaryDirectory() as srcdir:
            self.package.prebuild(self.env, srcdir)
            with open(
                os.path.join(srcdir, "configure.local"), encoding="utf-8"
            ) as config:
                contents = config.read()

        self.assertIn("HAVE_NANOSLEEP=1\n", contents)
        self.assertIn("HAVE_NTOHL=1\n", contents)
        self.assertIn("HAVE_RECVMSG=0\n", contents)
        self.assertIn("HAVE_WCHAR=0\n", contents)
        self.assertIn("NEED_GNU_SOURCE=1\n", contents)
        self.assertIn("BUILD_CATMAN=0\n", contents)
        self.assertIn("HAVE_WFLAG=0\n", contents)
        self.assertIn(self.env["CROSS_CC"], contents)
        self.assertIn(self.env["CROSS_AR"], contents)

    @mock.patch("packages.mandoc.package.steps.cmd")
    def test_configure_runs_upstream_script_in_place(self, cmd):
        self.package.configure(self.env, "/source")

        cmd.assert_called_once_with(
            ["/source/configure"], cwd="/source", env=self.env
        )

    def test_postdeploy_requires_formatter_and_rejects_man_alias(self):
        with tempfile.TemporaryDirectory() as deploydir:
            with self.assertRaisesRegex(RuntimeError, "was not installed"):
                self.package.postdeploy({}, "/source", deploydir)

            bindir = os.path.join(deploydir, "usr", "bin")
            os.makedirs(bindir)
            open(os.path.join(bindir, "mandoc"), "wb").close()
            self.package.postdeploy({}, "/source", deploydir)

            os.symlink("mandoc", os.path.join(bindir, "man"))
            with self.assertRaisesRegex(RuntimeError, "unexpectedly installed"):
                self.package.postdeploy({}, "/source", deploydir)


if __name__ == "__main__":
    unittest.main()
