import os
import unittest
from unittest import mock

from .package import CmakePackage


class CmakePackageTest(unittest.TestCase):
    @mock.patch("packages.cmake.package.steps.cmake_configure")
    def test_configure_disables_untranslated_libc_probes(
        self, cmake_configure
    ):
        package = CmakePackage(__file__)

        package.configure({}, "/source")

        extra_config = cmake_configure.call_args.kwargs["extra_config"]
        self.assertIn("-DCMAKE_USE_OPENSSL=ON", extra_config)
        self.assertIn(
            "-DCURL_CA_BUNDLE=/etc/ssl/cert.pem", extra_config
        )
        self.assertNotIn("-DCMAKE_USE_OPENSSL=OFF", extra_config)
        for option in (
            "-DHAVE_FSETXATTR=0",
            "-DHAVE_FSETXATTR_5=0",
            "-DHAVE_LCHMOD=0",
            "-DHAVE_LUTIMES=0",
            "-DHAVE_UTIMENSAT=0",
            "-DKWSYS_CXX_HAS_GETLOADAVG_COMPILED=0",
            "-DKWSYS_CXX_HAS_UTIMENSAT_COMPILED=0",
        ):
            with self.subTest(option=option):
                self.assertIn(option, extra_config)

    def test_runtime_patch_follows_platform_patch(self):
        package = CmakePackage(__file__)

        self.assertEqual(
            package.patches({}, "/source"),
            ["libuv-pedigree.diff", "pedigree-runtime-apis.diff"],
        )

    def test_runtime_patch_reports_unsupported_apis_without_dead_syscalls(self):
        patch_path = os.path.join(
            os.path.dirname(__file__),
            "patches",
            "pedigree-runtime-apis.diff",
        )
        with open(patch_path, encoding="utf-8") as patch_file:
            patch = patch_file.read()

        self.assertIn("+        kill(getpid(), signum);", patch)
        self.assertGreaterEqual(patch.count("+  return UV_ENOSYS;"), 3)
        self.assertIn("+        r = uv__pread(fd, p, n, off);", patch)
        self.assertIn("+        r = uv__pwrite(fd, p, n, off);", patch)
        self.assertIn("+    X(LCHOWN, (errno = ENOSYS, -1));", patch)
        self.assertIn(
            "static ssize_t uv__fs_copyfile(uv_fs_t* req) {\n"
            "+#if defined(__pedigree__)\n"
            "+  (void) req;\n"
            "+  errno = ENOSYS;",
            patch,
        )


if __name__ == "__main__":
    unittest.main()
