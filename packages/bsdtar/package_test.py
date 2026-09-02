import unittest
from unittest import mock

from .package import BsdtarPackage


class BsdtarPackageTest(unittest.TestCase):
    @mock.patch("packages.bsdtar.package.steps.run_configure")
    def test_configure_disables_staged_dependency_rpaths(self, run_configure):
        env = {
            "PORTS_SYSROOT": "/build/stage",
            "TARGET_SYSROOT": "/toolchain/target",
        }
        BsdtarPackage(__file__).configure(env, "/source")

        self.assertIn(
            "--disable-rpath",
            run_configure.call_args.kwargs["extra_config"],
        )
        self.assertEqual(
            env["lt_cv_sys_lib_dlsearch_path_spec"],
            "/build/stage/usr/lib /lib /usr/lib",
        )
        self.assertEqual(
            env["lt_cv_sys_lib_search_path_spec"],
            "/build/stage/usr/lib /toolchain/target/lib "
            "/toolchain/target/usr/lib",
        )


if __name__ == "__main__":
    unittest.main()
