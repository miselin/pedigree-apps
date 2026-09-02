import os
import tempfile
import unittest

from .package import GawkPackage


class GawkPackageTest(unittest.TestCase):
    def test_postdeploy_sanitizes_gawkbug_build_metadata(self):
        with tempfile.TemporaryDirectory() as deploydir:
            bindir = os.path.join(deploydir, "usr", "bin")
            os.makedirs(bindir)

            env = {
                "APPS_BASE": "/workspace",
                "CROSS_BASE": "/opt/pedigree",
                "CROSS_CC": (
                    "/opt/pedigree/bin/x86_64-pedigree-gcc"
                ),
                "PORTS_SYSROOT": (
                    "/workspace/.build/x86_64/sysroots/gawk"
                ),
                "TARGET_SYSROOT": "/opt/pedigree/x86_64-pedigree",
            }
            gawkbug = os.path.join(bindir, "gawkbug")
            with open(gawkbug, "w", encoding="utf-8") as script:
                script.write(
                    '#!/bin/sh\n'
                    'CC="%s"\n'
                    'CFLAGS="-O2 -I%s/usr/include '
                    '-I/usr/include/gawk --sysroot=%s '
                    '-Wl,-rpath-link,%s/usr/lib"\n'
                    % (
                        env["CROSS_CC"],
                        env["PORTS_SYSROOT"],
                        env["TARGET_SYSROOT"],
                        env["PORTS_SYSROOT"],
                    )
                )

            GawkPackage(__file__).postdeploy(env, "", deploydir)

            with open(gawkbug, encoding="utf-8") as script:
                contents = script.read()
            self.assertIn('CC="gcc"', contents)
            self.assertIn("-I/usr/include", contents)
            self.assertIn("-I/usr/include/gawk", contents)
            self.assertNotIn("--sysroot", contents)
            self.assertNotIn("rpath-link", contents)
            self.assertNotIn(env["CROSS_BASE"], contents)
            self.assertNotIn(env["PORTS_SYSROOT"], contents)


if __name__ == "__main__":
    unittest.main()
