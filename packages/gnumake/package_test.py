import unittest
from unittest import mock

from .package import GnumakePackage


class GnumakePackageTest(unittest.TestCase):
    @mock.patch("packages.gnumake.package.steps.run_configure")
    def test_configure_does_not_mask_getloadavg(self, configure):
        env = {}

        GnumakePackage(__file__).configure(env, "/source")

        self.assertNotIn("ac_cv_func_getloadavg", env)
        self.assertNotIn("ac_cv_lib_util_getloadavg", env)
        configure.assert_called_once()


if __name__ == "__main__":
    unittest.main()
