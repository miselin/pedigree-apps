import os
import tempfile
import unittest

from .package import LibgmpPackage


class LibgmpPackageTest(unittest.TestCase):
    def setUp(self):
        self.env = {
            "CROSS_BASE": "/opt/pedigree",
            "CROSS_CC": "/opt/pedigree/bin/x86_64-pedigree-gcc",
            "PORTS_SYSROOT": "/workspace/.build/x86_64/sysroots/libgmp",
        }

    def _write_header(self, deploydir, contents):
        include = os.path.join(deploydir, "usr", "include")
        os.makedirs(include)
        header = os.path.join(include, "gmp.h")
        with open(header, "w", encoding="utf-8") as metadata:
            metadata.write(contents)
        return header

    def test_no_legacy_raise_workaround_is_applied(self):
        self.assertEqual(LibgmpPackage(__file__).patches({}, ""), [])

    def test_postdeploy_rewrites_only_compiler_descriptor(self):
        with tempfile.TemporaryDirectory() as deploydir:
            before = (
                "#define GMP_VERSION \"6.3.0\"\n"
                "#define __GMP_CC \"%s\"\n"
                "#define __GMP_CFLAGS \"-O2 -pipe -D__PEDIGREE__\"\n"
                "#define GMP_LIMB_BITS 64\n"
                % self.env["CROSS_CC"]
            )
            header = self._write_header(deploydir, before)

            LibgmpPackage(__file__).postdeploy(self.env, "", deploydir)

            with open(header, encoding="utf-8") as metadata:
                after = metadata.read()
            self.assertEqual(
                after,
                before.replace(
                    '#define __GMP_CC "%s"' % self.env["CROSS_CC"],
                    '#define __GMP_CC "gcc"',
                ),
            )
            self.assertIn(
                '#define __GMP_CFLAGS "-O2 -pipe -D__PEDIGREE__"',
                after,
            )

    def test_postdeploy_requires_expected_compiler_metadata(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self._write_header(
                deploydir,
                '#define __GMP_CC "cc"\n#define __GMP_CFLAGS "-O2"\n',
            )

            with self.assertRaisesRegex(
                RuntimeError, "compiler metadata was not as expected"
            ):
                LibgmpPackage(__file__).postdeploy(
                    self.env, "", deploydir
                )

    def test_postdeploy_requires_compiler_flags_metadata(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self._write_header(
                deploydir,
                '#define __GMP_CC "%s"\n' % self.env["CROSS_CC"],
            )

            with self.assertRaisesRegex(
                RuntimeError, "compiler flags metadata was not installed"
            ):
                LibgmpPackage(__file__).postdeploy(
                    self.env, "", deploydir
                )

    def test_postdeploy_rejects_residual_build_paths(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self._write_header(
                deploydir,
                (
                    '#define __GMP_CC "%s"\n'
                    '#define __GMP_CFLAGS "-I%s/usr/include"\n'
                    % (self.env["CROSS_CC"], self.env["PORTS_SYSROOT"])
                ),
            )

            with self.assertRaisesRegex(
                RuntimeError, "contains build paths"
            ):
                LibgmpPackage(__file__).postdeploy(
                    self.env, "", deploydir
                )

    def test_postdeploy_requires_installed_header(self):
        with tempfile.TemporaryDirectory() as deploydir:
            with self.assertRaisesRegex(
                RuntimeError, "development metadata was not installed"
            ):
                LibgmpPackage(__file__).postdeploy(
                    self.env, "", deploydir
                )


if __name__ == "__main__":
    unittest.main()
