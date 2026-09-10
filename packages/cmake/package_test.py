import unittest
from unittest import mock

from .package import CmakePackage


class CmakePackageTest(unittest.TestCase):
    @mock.patch("packages.cmake.package.steps.cmake_configure")
    def test_configure_disables_only_unimplemented_libc_probes(
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
        self.assertIn("-DHAVE_SENDMMSG=0", extra_config)
        for option in (
            "-DHAVE_FSETXATTR=0",
            "-DHAVE_FSETXATTR_5=0",
            "-DKWSYS_CXX_HAS_GETLOADAVG_COMPILED=0",
        ):
            self.assertNotIn(option, extra_config)

    def test_runtime_patch_follows_platform_patch(self):
        package = CmakePackage(__file__)

        self.assertEqual(
            package.patches({}, "/source"),
            ["libuv-pedigree.diff"],
        )


if __name__ == "__main__":
    unittest.main()
