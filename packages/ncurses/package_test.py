import os
import tempfile
import unittest

from .package import NcursesPackage


class NcursesPackageTest(unittest.TestCase):
    def test_postdeploy_sanitizes_config_and_pkgconfig_paths(self):
        with tempfile.TemporaryDirectory() as deploydir:
            bindir = os.path.join(deploydir, "usr", "bin")
            pkgconfig_dir = os.path.join(
                deploydir, "usr", "lib", "pkgconfig")
            os.makedirs(bindir)
            os.makedirs(pkgconfig_dir)

            sysroot = "/workspace/.build/x86_64/sysroots/ncurses"
            build_flags = (
                "-L%s/usr/lib -Wl,-rpath-link,%s/usr/lib"
                % (sysroot, sysroot)
            )
            config = os.path.join(bindir, "ncursesw6-config")
            with open(config, "w", encoding="utf-8") as script:
                script.write("#!/bin/sh\necho '%s -lncursesw'\n" % build_flags)
            for name in ("ncursesw.pc", "tinfow.pc"):
                with open(
                    os.path.join(pkgconfig_dir, name),
                    "w",
                    encoding="utf-8",
                ) as metadata:
                    metadata.write("prefix=/usr\nLibs: %s -ltinfow\n" % build_flags)

            NcursesPackage(__file__).postdeploy(
                {"PORTS_SYSROOT": sysroot}, "", deploydir)

            for path in (
                config,
                os.path.join(pkgconfig_dir, "ncursesw.pc"),
                os.path.join(pkgconfig_dir, "tinfow.pc"),
            ):
                with open(path, encoding="utf-8") as metadata:
                    contents = metadata.read()
                self.assertNotIn(sysroot, contents)
                self.assertNotIn("rpath-link", contents)


if __name__ == "__main__":
    unittest.main()
