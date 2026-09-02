import os
import tempfile
import unittest
from unittest import mock

from .package import MesaPackage


class MesaPackageTest(unittest.TestCase):
    def _write_shared_profile(self, deploydir, include_static=False):
        libdir = os.path.join(deploydir, "usr", "lib")
        os.makedirs(os.path.join(deploydir, "usr", "include", "GL"))
        os.makedirs(os.path.join(libdir, "pkgconfig"))
        artifacts = [
            os.path.join("usr", "include", "GL", "osmesa.h"),
            os.path.join("usr", "lib", "libOSMesa.so.8.0.0"),
            os.path.join("usr", "lib", "pkgconfig", "osmesa.pc"),
        ]
        if include_static:
            artifacts.append(os.path.join("usr", "lib", "libOSMesa.a"))
        for relative in artifacts:
            with open(os.path.join(deploydir, relative), "wb") as artifact:
                artifact.write(b"fixture")
        os.symlink(
            "libOSMesa.so.8.0.0",
            os.path.join(libdir, "libOSMesa.so.8"),
        )
        os.symlink("libOSMesa.so.8", os.path.join(libdir, "libOSMesa.so"))

    @mock.patch("packages.mesa.package.steps.meson_configure")
    def test_uses_final_osmesa_release_and_software_renderer(
        self, meson_configure
    ):
        package = MesaPackage(__file__)

        self.assertEqual(package.version(), "25.0.7")
        package.configure({}, "/source")

        options = meson_configure.call_args.kwargs["extra_config"]
        for option in (
            "-Ddefault_library=shared",
            "-Dplatforms=",
            "-Dgallium-drivers=softpipe",
            "-Dosmesa=true",
            "-Dllvm=disabled",
            "-Dshader-cache=disabled",
        ):
            with self.subTest(option=option):
                self.assertIn(option, options)
        self.assertNotIn("-Ddefault_library=both", options)

    def test_postdeploy_requires_shared_osmesa_abi(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self._write_shared_profile(deploydir)

            MesaPackage(__file__).postdeploy({}, "", deploydir)

    def test_postdeploy_rejects_invalid_shared_abi_link(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self._write_shared_profile(deploydir)
            link_path = os.path.join(
                deploydir, "usr", "lib", "libOSMesa.so"
            )
            os.unlink(link_path)
            os.symlink("libOSMesa.so.8.0.0", link_path)

            with self.assertRaisesRegex(RuntimeError, "shared ABI link"):
                MesaPackage(__file__).postdeploy({}, "", deploydir)

    def test_postdeploy_rejects_static_osmesa_claim(self):
        with tempfile.TemporaryDirectory() as deploydir:
            self._write_shared_profile(deploydir, include_static=True)

            with self.assertRaisesRegex(RuntimeError, "static library"):
                MesaPackage(__file__).postdeploy({}, "", deploydir)

    def test_pedigree_patch_covers_target_runtime_contract(self):
        package = MesaPackage(__file__)
        self.assertEqual(
            package.patches({}, "/source"), ["pedigree-platform.diff"]
        )

        patch_path = os.path.join(
            os.path.dirname(__file__), "patches", "pedigree-platform.diff"
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn("DETECT_OS_PEDIGREE", patch)
        self.assertIn("'memfd_create', 'posix_fallocate'", patch)
        self.assertIn("host_machine.system() != 'pedigree'", patch)
        self.assertIn("pedigree_unavailable_headers = ['sys/inotify.h']", patch)

        blake3_assembly = (
            "blake3_avx2_x86-64_unix.S",
            "blake3_avx512_x86-64_unix.S",
            "blake3_sse2_x86-64_unix.S",
            "blake3_sse41_x86-64_unix.S",
        )
        for filename in blake3_assembly:
            with self.subTest(filename=filename):
                self.assertIn(
                    "diff --git a/src/util/blake3/%s "
                    "b/src/util/blake3/%s" % (filename, filename),
                    patch,
                )
        pedigree_stack_guard = (
            "+#if defined(__ELF__) && "
            "(defined(__linux__) || defined(__pedigree__))"
        )
        self.assertEqual(patch.count(pedigree_stack_guard), 4)


if __name__ == "__main__":
    unittest.main()
