import unittest
from unittest import mock

from .package import GnumakePackage


class GnumakePackageTest(unittest.TestCase):
    @mock.patch("packages.gnumake.package.steps.run_configure")
    def test_configure_selects_bundled_getloadavg_fallback(self, configure):
        env = {}

        GnumakePackage(__file__).configure(env, "/source")

        self.assertEqual(env["ac_cv_func_getloadavg"], "no")
        self.assertEqual(env["ac_cv_lib_util_getloadavg"], "no")
        configure.assert_called_once()


if __name__ == "__main__":
    unittest.main()
