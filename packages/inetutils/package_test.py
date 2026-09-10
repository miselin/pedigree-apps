import pathlib
import unittest
from unittest import mock

from .package import InetutilsPackage, MAKE_OPTIONS


class InetutilsPackageTest(unittest.TestCase):
    def test_build_keeps_distributed_man_pages_in_cross_build(self):
        self.assertEqual(MAKE_OPTIONS, ("HELP2MAN=true",))

    @mock.patch("packages.inetutils.package.steps.run_configure")
    def test_configure_disables_staged_dependency_rpaths(self, run_configure):
        InetutilsPackage(__file__).configure({}, "/source")

        self.assertIn(
            "--disable-rpath",
            run_configure.call_args.kwargs["extra_config"],
        )


if __name__ == "__main__":
    unittest.main()
