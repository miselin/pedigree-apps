import hashlib
import os
import tempfile
import unittest
from unittest import mock

from .package import (
    MAINLINE_PATCH_SHA256,
    SOURCE_VERSION,
    TOOLCHAIN_RECIPE,
    BinutilsPackage,
)


class BinutilsPackageTest(unittest.TestCase):

    def setUp(self):
        self.package = BinutilsPackage(__file__)
        self.env = {
            "CROSS_AR": "/opt/pedigree/bin/x86_64-pedigree-ar",
            "CROSS_AS": "/opt/pedigree/bin/x86_64-pedigree-as",
            "CROSS_BASE": "/opt/pedigree",
            "CROSS_CC": "/opt/pedigree/bin/x86_64-pedigree-gcc",
            "CROSS_CXX": "/opt/pedigree/bin/x86_64-pedigree-g++",
            "CROSS_LD": "/opt/pedigree/bin/x86_64-pedigree-ld",
            "CROSS_RANLIB": "/opt/pedigree/bin/x86_64-pedigree-ranlib",
            "CROSS_TARGET": "x86_64-pedigree",
            "LDFLAGS": "-Wl,-z,max-page-size=4096",
            "MAKE": "/usr/bin/make",
            "MAKEFLAGS": "-j8",
            "PORTS_SYSROOT": "/workspace/.build/x86_64/sysroots/binutils",
            "TARGET_CONFIG_SITE": "/workspace/config.site",
        }

    def test_matches_mainline_r2_manifest_and_patch(self):
        self.assertEqual(self.package.version(), "2.46.1")
        self.assertEqual(SOURCE_VERSION, "2.46.1")
        self.assertEqual(TOOLCHAIN_RECIPE, 2)
        patch_path = os.path.join(
            os.path.dirname(__file__), "patches", "pedigree-binutils.diff"
        )
        with open(patch_path, "rb") as patch_file:
            digest = hashlib.sha256(patch_file.read()).hexdigest()
        self.assertEqual(digest, MAINLINE_PATCH_SHA256)

    @mock.patch("packages.binutils.package.steps.download")
    def test_download_is_digest_pinned(self, download):
        self.package.download({}, "/download")

        args = download.call_args.args
        self.assertEqual(
            args[0],
            "https://sourceware.org/pub/binutils/releases/"
            "binutils-2.46.1.tar.xz",
        )
        self.assertEqual(
            download.call_args.kwargs["sha256"],
            "e127a709cba24c76de8936cb7083dd768f28cd37eb010492e2f19b71eb1294e4",
        )

    @mock.patch("packages.binutils.package.steps.cmd")
    @mock.patch(
        "packages.binutils.package.steps.cmd_output",
        return_value="x86_64-pc-linux-gnu\n",
    )
    @mock.patch(
        "packages.binutils.package.shutil.which",
        side_effect=lambda name: "/usr/bin/" + name,
    )
    def test_configure_is_target_native_canadian_cross(
        self, which, cmd_output, cmd
    ):
        with tempfile.TemporaryDirectory() as srcdir:
            self.package.configure(self.env, srcdir)

        command = cmd.call_args.args[0]
        command_env = cmd.call_args.kwargs["env"]
        self.assertIn("--build=x86_64-pc-linux-gnu", command)
        self.assertIn("--host=x86_64-pedigree", command)
        self.assertIn("--target=x86_64-pedigree", command)
        self.assertIn("--with-sysroot=/", command)
        self.assertNotIn(
            "--with-sysroot=" + self.env["PORTS_SYSROOT"], command
        )
        self.assertIn("--with-system-zlib", command)
        self.assertIn("--without-zstd", command)
        self.assertEqual(command_env["CC_FOR_BUILD"], "/usr/bin/cc")
        self.assertEqual(command_env["CC_FOR_TARGET"], self.env["CROSS_CC"])
        self.assertEqual(
            command_env["CONFIG_SITE"], self.env["TARGET_CONFIG_SITE"]
        )

    def test_runtime_contract_includes_native_linker_dependency(self):
        self.assertEqual(self.package.build_requires(), ["zlib"])
        self.assertEqual(self.package.install_deps(), ["zlib"])

    def test_patch_carries_current_bfd_gas_and_ld_targets(self):
        patch_path = os.path.join(
            os.path.dirname(__file__), "patches", "pedigree-binutils.diff"
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn("x86_64-*-pedigree*", patch)
        self.assertIn("i386-*-pedigree*)", patch)
        self.assertIn("targ_emul=elf_x86_64", patch)
        self.assertIn("targ_extra_emuls=elf_i386", patch)
        self.assertNotIn("pedigree_x86_64.sh", patch)

    def test_postdeploy_removes_libtool_metadata_and_requires_native_tools(self):
        with tempfile.TemporaryDirectory() as deploydir:
            bindir = os.path.join(deploydir, "usr", "bin")
            libdir = os.path.join(deploydir, "usr", "lib")
            os.makedirs(bindir)
            os.makedirs(libdir)
            for name in ("as", "ld", "objdump", "readelf"):
                open(os.path.join(bindir, name), "wb").close()
            archive = os.path.join(libdir, "libbfd.la")
            open(archive, "wb").close()

            self.package.postdeploy(self.env, "/source", deploydir)

            self.assertFalse(os.path.exists(archive))


if __name__ == "__main__":
    unittest.main()
